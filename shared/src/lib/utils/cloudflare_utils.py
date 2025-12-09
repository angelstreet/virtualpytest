#!/usr/bin/env python3

"""
Cloudflare R2 Utilities for VirtualPyTest Resources

Utilities for uploading and downloading files from Cloudflare R2 with public access.

Folder Structure:
- reference-images/{userinterface_name}/{image_name}     # Reference images (public access)
- navigation/{userinterface_name}/{screenshot_name} # Navigation screenshots (public access)
"""

import os
import boto3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from mimetypes import guess_type
import logging
from botocore.client import Config
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configure module-specific logging (avoid global basicConfig)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add handler if not already present (avoid duplicate handlers)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[@cloudflare_utils:%(funcName)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False  # Prevent propagation to root logger

# R2 rejects presigned URLs with X-Amz-Expires >= 604800 seconds (7 days).
# Use a safe ceiling of 604799s to stay under the limit.
MAX_R2_PRESIGN_EXPIRY = 604_799

class CloudflareUtils:
    """
    Singleton Cloudflare R2 utility for VirtualPyTest resources.
    Upload and download files and get signed URLs.
    
    This class implements the singleton pattern to ensure only one instance
    exists throughout the application lifecycle, avoiding multiple S3 client
    initializations.
    
    Configuration:
    - Environment variables should be loaded by the main application (app_utils.load_environment_variables)
    - Requires: CLOUDFLARE_R2_ENDPOINT, CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_ACCESS_KEY
    - Endpoint URL should NOT include bucket name (e.g., https://account.r2.cloudflarestorage.com)
    - Bucket name is passed separately to boto3 operations
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern implementation - only create one instance."""
        if cls._instance is None:
            logger.info("Creating new CloudflareUtils singleton instance")
            cls._instance = super().__new__(cls)
        else:
            logger.debug("Returning existing CloudflareUtils singleton instance")
        return cls._instance
    
    def __init__(self):
        """Initialize the utility (only once due to singleton)."""
        # Prevent re-initialization of the singleton instance
        if self._initialized:
            return
            
        logger.info("Initializing CloudflareUtils singleton")
        
        # Use 'virtualpytest' as bucket name (boto3 requires valid bucket name)
        self.bucket_name = 'virtualpytest'
        self.s3_client = self._init_s3_client()
        self._initialized = True
    
    def _init_s3_client(self):
        """Initialize S3 client for Cloudflare R2."""
        try:
            endpoint_url = os.environ.get('CLOUDFLARE_R2_ENDPOINT')
            access_key = os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID')
            secret_key = os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
            
            if not all([endpoint_url, access_key, secret_key]):
                missing_vars = []
                if not endpoint_url:
                    missing_vars.append('CLOUDFLARE_R2_ENDPOINT')
                if not access_key:
                    missing_vars.append('CLOUDFLARE_R2_ACCESS_KEY_ID')
                if not secret_key:
                    missing_vars.append('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
                raise ValueError(f"Missing required Cloudflare R2 environment variables: {', '.join(missing_vars)}")
            
            logger.info("Initializing S3 client for Cloudflare R2")
            logger.info(f"Using endpoint: {endpoint_url}")
            logger.info(f"Using bucket: {self.bucket_name}")
            
            # Configure aggressive timeouts and retries to prevent long hangs
            # Reference image downloads should be fast - if they're slow, fail fast
            config = Config(
                signature_version='s3v4',
                connect_timeout=5,      # 5 seconds to establish connection
                read_timeout=10,        # 10 seconds to read response
                retries={
                    'max_attempts': 2,  # Only retry once (total 2 attempts)
                    'mode': 'standard'
                }
            )
            
            return boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto',  # Required for Cloudflare R2 signed URLs
                config=config
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Cloudflare R2 client: {str(e)}")
            raise
    
    def upload_files(self, file_mappings: List[Dict], max_workers: int = 10, auto_delete_cold: bool = True, for_report_assets: bool = False) -> Dict:
        """
        Upload files concurrently.
        
        Args:
            file_mappings: List of dicts with 'local_path' and 'remote_path' keys
            max_workers: Max concurrent uploads
            auto_delete_cold: Whether to delete cold storage files after upload
            for_report_assets: If True, return URLs suitable for HTML reports (14-day signed URLs in private mode)
            Optional 'content_type' key to override auto-detection
            max_workers: Maximum number of concurrent upload threads
            auto_delete_cold: If True, automatically delete files from cold storage after successful upload
            
        Returns:
            Dict with upload results
        """
        uploaded_files = []
        failed_uploads = []
        deleted_files = []
        
        # Deduplicate file_mappings by local_path to prevent race conditions
        # Keep first occurrence of each unique local_path
        seen_paths = {}
        deduplicated_mappings = []
        duplicate_count = 0
        
        for mapping in file_mappings:
            local_path = mapping['local_path']
            if local_path not in seen_paths:
                seen_paths[local_path] = mapping
                deduplicated_mappings.append(mapping)
            else:
                duplicate_count += 1
                # Log duplicate for debugging - helps identify the source
                logger.debug(f"Skipping duplicate upload request for {local_path} (remote: {mapping['remote_path']})")
        
        if duplicate_count > 0:
            logger.info(f"Deduplicated {duplicate_count} duplicate file(s) from upload batch (original: {len(file_mappings)}, unique: {len(deduplicated_mappings)})")
        
        # Use deduplicated mappings for upload
        file_mappings = deduplicated_mappings
        
        def upload_single_file(mapping):
            local_path = mapping['local_path']
            remote_path = mapping['remote_path']
            custom_content_type = mapping.get('content_type')
            
            try:
                if not os.path.exists(local_path):
                    return {
                        'success': False,
                        'local_path': local_path,
                        'remote_path': remote_path,
                        'error': f"File not found: {local_path}"
                    }
                
                # Use custom content type if provided, otherwise auto-detect
                if custom_content_type:
                    content_type = custom_content_type
                else:
                    content_type, _ = guess_type(local_path)
                    if not content_type:
                        content_type = 'application/octet-stream'
                
                # Add mtime metadata for capture files
                extra_args = {'ContentType': content_type}
                if 'capture_' in os.path.basename(local_path) and local_path.endswith('.jpg'):
                    capture_time = str(int(os.path.getmtime(local_path)))
                    extra_args['Metadata'] = {'capture_time': capture_time}
                
                file_size = os.path.getsize(local_path)
                
                with open(local_path, 'rb') as f:
                    self.s3_client.upload_fileobj(
                        f,
                        self.bucket_name,
                        remote_path,
                        ExtraArgs=extra_args
                    )
                
                # Get URL based on use case
                if for_report_assets:
                    # Report assets need long-lived URLs (14-day signed URLs in private mode)
                    file_url = self.get_url_for_report_asset(remote_path)
                else:
                    # Normal uploads use public URL or path
                    file_url = self.get_public_url(remote_path)
                
                result = {
                    'success': True,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'url': file_url,
                    'size': file_size,
                    'deleted': False
                }
                
                # Auto-delete from cold storage after successful upload
                # Only delete if file is in cold storage (not hot) and contains "capture_" or "thumbnail"
                if auto_delete_cold:
                    is_cold_file = (
                        ('/captures/' in local_path or '/thumbnails/' in local_path) and
                        '/hot/' not in local_path and
                        ('capture_' in os.path.basename(local_path) or 'thumbnail' in os.path.basename(local_path))
                    )
                    
                    if is_cold_file:
                        try:
                            # Check if file still exists before attempting deletion (race condition safety)
                            if os.path.exists(local_path):
                                os.remove(local_path)
                                result['deleted'] = True
                                logger.debug(f"Auto-deleted cold file after upload: {local_path}")
                            else:
                                logger.debug(f"Cold file already deleted (likely by another process): {local_path}")
                        except FileNotFoundError:
                            # File was deleted between the exists check and remove call
                            logger.debug(f"Cold file already deleted during removal: {local_path}")
                        except Exception as del_error:
                            logger.warning(f"Failed to auto-delete cold file {local_path}: {del_error}")
                
                return result
                
            except Exception as e:
                return {
                    'success': False,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'error': str(e)
                }
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(upload_single_file, mapping) for mapping in file_mappings]
            
            for future in as_completed(futures):
                result = future.result()
                
                if result['success']:
                    uploaded_files.append(result)
                    if result.get('deleted'):
                        deleted_files.append(result['local_path'])
                else:
                    failed_uploads.append(result)
        
        response = {
            'success': len(failed_uploads) == 0,
            'uploaded_count': len(uploaded_files),
            'failed_count': len(failed_uploads),
            'uploaded_files': uploaded_files,
            'failed_uploads': failed_uploads
        }
        
        if deleted_files:
            response['deleted_count'] = len(deleted_files)
            response['deleted_files'] = deleted_files
            logger.info(f"Auto-deleted {len(deleted_files)} cold storage files after upload")
        
        return response
    
    def download_file(self, remote_path: str, local_path: str) -> Dict:
        """
        Download a file from R2.
        
        Args:
            remote_path: Path in R2 (e.g., 'reference/android_mobile/default_capture.png')
            local_path: Path to save the file locally
            
        Returns:
            Dict with success status, local file path, and ETag
        """
        start_time = time.time()
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            logger.debug(f"Starting download: {remote_path}")
            
            # Download file using bucket name and get response metadata
            # With config timeouts: connect_timeout=5s, read_timeout=10s, max 2 attempts
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            
            fetch_time = time.time() - start_time
            if fetch_time > 1.0:
                logger.warning(f"Slow R2 fetch: {remote_path} took {fetch_time:.2f}s to get response")
            
            # Write file content
            with open(local_path, 'wb') as f:
                f.write(response['Body'].read())
            
            write_time = time.time() - start_time - fetch_time
            total_time = time.time() - start_time
            
            # Extract ETag from response metadata
            etag = response.get('ETag', '').strip('"')
            file_size = os.path.getsize(local_path)
            
            # Log with timing details
            if total_time > 2.0:
                logger.warning(f"Downloaded: {remote_path} -> {local_path} (ETag: {etag[:8]}...) - SLOW: {total_time:.2f}s (fetch: {fetch_time:.2f}s, write: {write_time:.2f}s, size: {file_size} bytes)")
            else:
                logger.info(f"Downloaded: {remote_path} -> {local_path} (ETag: {etag[:8]}...) - {total_time:.2f}s ({file_size} bytes)")
            
            return {
                'success': True,
                'remote_path': remote_path,
                'local_path': local_path,
                'size': file_size,
                'etag': etag,
                'download_time': total_time
            }
            
        except ClientError as e:
            elapsed = time.time() - start_time
            if e.response['Error']['Code'] == '404':
                logger.error(f"File not found in R2: {remote_path} (failed after {elapsed:.2f}s)")
                return {'success': False, 'error': f"File not found in R2: {remote_path}"}
            else:
                logger.error(f"Download failed: {str(e)} (failed after {elapsed:.2f}s)")
                return {'success': False, 'error': str(e)}
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Download failed: {str(e)} (failed after {elapsed:.2f}s)")
            return {'success': False, 'error': str(e)}
    
    def head_file(self, remote_path: str) -> Dict:
        """
        Get file metadata from R2 without downloading (HTTP HEAD request).
        Useful for checking if file changed (via ETag) or getting Last-Modified date.
        
        Args:
            remote_path: Path in R2 (e.g., 'reference-images/horizon_tv/apps_oneplus.jpg')
            
        Returns:
            Dict with success status, etag, last_modified, and content_length
        """
        start_time = time.time()
        try:
            # HEAD request with same timeout config as downloads (5s connect, 10s read)
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=remote_path
            )
            
            elapsed = time.time() - start_time
            
            etag = response.get('ETag', '').strip('"')
            last_modified = response.get('LastModified')
            content_length = response.get('ContentLength', 0)
            
            if elapsed > 1.0:
                logger.warning(f"HEAD: {remote_path} (ETag: {etag[:8]}..., Size: {content_length} bytes) - SLOW: {elapsed:.2f}s")
            else:
                logger.debug(f"HEAD: {remote_path} (ETag: {etag[:8]}..., Size: {content_length} bytes) - {elapsed:.2f}s")
            
            return {
                'success': True,
                'etag': etag,
                'last_modified': last_modified,
                'content_length': content_length,
                'request_time': elapsed
            }
            
        except ClientError as e:
            elapsed = time.time() - start_time
            if e.response['Error']['Code'] == '404':
                logger.error(f"File not found in R2: {remote_path} (failed after {elapsed:.2f}s)")
                return {'success': False, 'error': f"File not found in R2: {remote_path}"}
            else:
                logger.error(f"HEAD request failed: {str(e)} (failed after {elapsed:.2f}s)")
                return {'success': False, 'error': str(e)}
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"HEAD request failed: {str(e)} (failed after {elapsed:.2f}s)")
            return {'success': False, 'error': str(e)}
    
    def copy_file(self, source_path: str, destination_path: str) -> Dict:
        """
        Copy a file within R2 storage (server-side copy).
        
        Args:
            source_path: Source path in R2 (e.g., 'navigation/android_mobile/Home.jpg')
            destination_path: Destination path in R2 (e.g., 'navigation/horizon_android_mobile/Home.jpg')
            
        Returns:
            Dict with success status and new file URL
        """
        try:
            # Use S3 copy_object for efficient server-side copy
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_path
            }
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_path
            )
            
            new_url = self.get_public_url(destination_path)
            
            logger.info(f"Copied in R2: {source_path} -> {destination_path}")
            
            return {
                'success': True,
                'source_path': source_path,
                'destination_path': destination_path,
                'url': new_url
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.error(f"Source file not found in R2: {source_path}")
                return {'success': False, 'error': f"Source file not found: {source_path}"}
            else:
                logger.error(f"Copy failed: {str(e)}")
                return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Copy failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def is_public_mode(self) -> bool:
        """
        Check if public URL mode is enabled.
        
        Returns:
            True if CLOUDFLARE_R2_PUBLIC_URL is set (public bucket mode)
            False if not set (private bucket mode - use signed URLs)
        """
        public_url_base = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', '').strip()
        return bool(public_url_base)
    
    def get_file_url_or_path(self, remote_path: str) -> str:
        """
        Get the appropriate reference for a file in R2.
        
        In PUBLIC mode (CLOUDFLARE_R2_PUBLIC_URL is set):
            Returns full public URL: https://pub-xxx.r2.dev/captures/file.jpg
        
        In PRIVATE mode (CLOUDFLARE_R2_PUBLIC_URL is NOT set):
            Returns just the path: captures/file.jpg
            (Frontend will use this path to request signed URLs)
        
        Args:
            remote_path: Path in R2 (e.g., 'captures/device1/screenshot.jpg')
            
        Returns:
            Full public URL (public mode) or just the path (private mode)
        """
        public_url_base = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', '').strip()
        
        if public_url_base:
            # PUBLIC MODE: Return full URL
            base_url = public_url_base.rstrip('/')
            return f"{base_url}/{remote_path}"
        else:
            # PRIVATE MODE: Return just the path
            # Frontend will use this to request signed URLs from backend
            logger.debug(f"Private mode: returning path only for {remote_path}")
            return remote_path
    
    def get_public_url(self, remote_path: str) -> str:
        """
        Get a public URL for a file in R2.
        
        DEPRECATED: Use get_file_url_or_path() instead for mode-aware behavior.
        This method is kept for backwards compatibility but now returns
        path-only in private mode (instead of empty string).
        
        Args:
            remote_path: Path in R2
            
        Returns:
            Public URL string (if public mode) or path (if private mode)
        """
        # Delegate to new mode-aware method
        return self.get_file_url_or_path(remote_path)
    
    def get_url_for_report_asset(self, remote_path: str) -> str:
        """
        Get URL for assets embedded in HTML reports (screenshots, videos).
        
        In PUBLIC mode: Returns public URL
        In PRIVATE mode: Returns signed URL with 14-day expiry
        
        This is specifically for HTML reports where we need working URLs
        that last longer than the typical 1-hour signed URL expiry.
        
        Args:
            remote_path: Path in R2 (e.g., 'script-reports/device/report/screenshot.jpg')
            
        Returns:
            URL string that works for 14 days (public URL or long-expiry signed URL)
        """
        if self.is_public_mode():
            # PUBLIC MODE: Return full public URL
            public_url_base = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', '').strip()
            base_url = public_url_base.rstrip('/')
            return f"{base_url}/{remote_path}"
        else:
            # PRIVATE MODE: Return signed URL capped at R2 max (must be < 604800s)
            result = self.generate_presigned_url(remote_path, expires_in=MAX_R2_PRESIGN_EXPIRY)
            
            if result.get('success'):
                logger.debug(f"Generated 14-day signed URL for report asset: {remote_path}")
                return result['url']
            else:
                # Fallback to path (will fail in browser but at least report generates)
                logger.warning(f"Failed to generate signed URL for {remote_path}, using path")
                return remote_path
    
    def generate_presigned_url(self, remote_path: str, expires_in: int = 3600) -> Dict:
        """
        Generate a pre-signed URL for secure, time-limited access to a private R2 file.
        
        This method creates a cryptographically signed URL that grants temporary access
        to a file in a private R2 bucket. The URL includes authentication parameters
        that R2 validates, eliminating the need for the bucket to be public.
        
        Args:
            remote_path: Path in R2 (e.g., 'captures/device1/capture_123.jpg')
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)
                       Common values: 1800 (30min), 3600 (1hr), 7200 (2hr), 86400 (24hr)
        
        Returns:
            Dict with:
                - success: bool - Whether URL generation succeeded
                - url: str - Pre-signed URL (if success=True)
                - expires_in: int - Seconds until expiration
                - expires_at: str - ISO timestamp of expiration
                - error: str - Error message (if success=False)
        
        Example:
            result = uploader.generate_presigned_url('verification/test.jpg', expires_in=7200)
            if result['success']:
                url = result['url']  # Valid for 2 hours
                # URL format: https://account.r2.cloudflarestorage.com/bucket/file.jpg?
                #             X-Amz-Algorithm=AWS4-HMAC-SHA256&
                #             X-Amz-Credential=...&
                #             X-Amz-Date=...&
                #             X-Amz-Expires=7200&
                #             X-Amz-SignedHeaders=host&
                #             X-Amz-Signature=...
        
        Notes:
            - Works with both public and private buckets
            - No API call to R2 - URL generated locally using credentials
            - URL can be cached until near expiration (save backend calls)
            - Free operation (no R2 API charges)
            - Requires CLOUDFLARE_R2_ACCESS_KEY_ID and SECRET_ACCESS_KEY
        """
        try:
            if not self.s3_client:
                logger.error("S3 client not initialized")
                return {
                    'success': False,
                    'error': 'R2 client not initialized'
                }
            
            # Strip leading slash from remote_path to prevent double slashes in signed URL
            # Example: "/heatmaps/file.jpg" -> "heatmaps/file.jpg"
            clean_remote_path = remote_path.lstrip('/')
            
            # Generate pre-signed URL using boto3
            # This creates a URL with AWS Signature Version 4 authentication
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': clean_remote_path
                },
                ExpiresIn=expires_in
            )
            
            # Calculate expiration timestamp
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info(f"Generated pre-signed URL for {remote_path} (expires in {expires_in}s)")
            
            return {
                'success': True,
                'url': presigned_url,
                'expires_in': expires_in,
                'expires_at': expires_at.isoformat() + 'Z',
                'remote_path': remote_path
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"Failed to generate pre-signed URL for {remote_path}: {error_code} - {error_msg}")
            return {
                'success': False,
                'error': f"R2 error: {error_code} - {error_msg}"
            }
        except Exception as e:
            logger.error(f"Failed to generate pre-signed URL for {remote_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_presigned_urls_batch(self, remote_paths: List[str], expires_in: int = 3600) -> Dict:
        """
        Generate multiple pre-signed URLs in a single call (for efficiency).
        
        Args:
            remote_paths: List of R2 paths
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)
        
        Returns:
            Dict with:
                - success: bool - Whether all URLs generated successfully
                - urls: List[Dict] - List of {path, url, expires_at} for successful URLs
                - failed: List[Dict] - List of {path, error} for failed URLs
                - generated_count: int
                - failed_count: int
        
        Example:
            paths = ['capture1.jpg', 'capture2.jpg', 'capture3.jpg']
            result = uploader.generate_presigned_urls_batch(paths, expires_in=3600)
            for item in result['urls']:
                print(f"{item['path']} -> {item['url']}")
        """
        urls = []
        failed = []
        
        for remote_path in remote_paths:
            result = self.generate_presigned_url(remote_path, expires_in)
            
            if result['success']:
                urls.append({
                    'path': remote_path,
                    'url': result['url'],
                    'expires_at': result['expires_at'],
                    'expires_in': expires_in
                })
            else:
                failed.append({
                    'path': remote_path,
                    'error': result.get('error', 'Unknown error')
                })
        
        logger.info(f"Generated {len(urls)}/{len(remote_paths)} pre-signed URLs (batch)")
        
        return {
            'success': len(failed) == 0,
            'urls': urls,
            'failed': failed,
            'generated_count': len(urls),
            'failed_count': len(failed)
        }
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from R2."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_path)
            logger.info(f"Deleted: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {str(e)}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in R2."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=remote_path)
            return True
        except ClientError:
            return False
    
    def test_connection(self) -> Dict:
        """Test the R2 connection and return diagnostic information."""
        try:
            # Test 1: List buckets
            response = self.s3_client.list_buckets()
            bucket_names = [bucket['Name'] for bucket in response['Buckets']]
            
            # Test 2: Check if our target bucket exists
            bucket_exists = self.bucket_name in bucket_names
            
            # Test 3: Try to access the bucket
            can_access_bucket = False
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                can_access_bucket = True
            except Exception as e:
                logger.error(f"Cannot access bucket: {e}")
            
            return {
                'success': True,
                'buckets_found': len(bucket_names),
                'bucket_names': bucket_names,
                'target_bucket_exists': bucket_exists,
                'can_access_bucket': can_access_bucket,
                'endpoint': os.environ.get('CLOUDFLARE_R2_ENDPOINT', 'NOT_SET'),
                'bucket_name': self.bucket_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'endpoint': os.environ.get('CLOUDFLARE_R2_ENDPOINT', 'NOT_SET'),
            }

# Singleton getter function
def get_cloudflare_utils() -> CloudflareUtils:
    """Get the singleton instance of CloudflareUtils."""
    return CloudflareUtils()

def convert_to_signed_url(url: str) -> str:
    """
    Convert R2 URL to signed URL. Simple utility like frontend's getR2Url.
    
    Args:
        url: R2 URL or path (e.g., 'https://pub-xxx.r2.dev/path/file.html' or 'path/file.html')
    
    Returns:
        Signed URL (returns original on error)
    """
    if not url or not ('r2.dev' in url or 'r2.cloudflarestorage.com' in url):
        return url
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        r2_path = parsed.path.lstrip('/')
        
        uploader = get_cloudflare_utils()
        result = uploader.generate_presigned_url(r2_path, expires_in=MAX_R2_PRESIGN_EXPIRY)
        return result['url'] if result.get('success') else url
    except Exception as e:
        logger.warning(f"Failed to convert to signed URL: {e}")
        return url

# Utility functions for common upload patterns

def upload_reference_image(local_path: str, userinterface_name: str, image_name: str) -> Dict:
    """
    Upload a reference image to R2 in the reference-images/{userinterface_name} folder.
    
    Args:
        local_path: Local path to the reference image file
        userinterface_name: Name of the user interface (e.g., 'horizon_android_mobile', 'perseus_360_web')
        image_name: Filename for the reference image (e.g., 'logo.jpg', 'button_play.jpg')
    
    Returns:
        Dict with success status, url, remote_path, and size
    """
    uploader = get_cloudflare_utils()
    remote_path = f"reference-images/{userinterface_name}/{image_name}"
    file_mappings = [{'local_path': local_path, 'remote_path': remote_path}]
    result = uploader.upload_files(file_mappings)
    
    # Return single file format for compatibility
    if result['uploaded_files']:
        return {
            'success': True,
            'url': result['uploaded_files'][0]['url'],
            'remote_path': result['uploaded_files'][0]['remote_path'],
            'size': result['uploaded_files'][0]['size']
        }
    else:
        return {
            'success': False,
            'error': result['failed_uploads'][0]['error'] if result['failed_uploads'] else 'Upload failed'
        }

def download_reference_image(userinterface_name: str, image_name: str, local_path: str) -> Dict:
    """
    Download a reference image from R2 in the reference-images/{userinterface_name} folder.
    
    Args:
        userinterface_name: Name of the user interface (e.g., 'horizon_android_mobile', 'perseus_360_web')
        image_name: Filename of the reference image
        local_path: Local path where the file should be saved
    
    Returns:
        Dict with success status and local file path
    """
    downloader = get_cloudflare_utils()
    remote_path = f"reference-images/{userinterface_name}/{image_name}"
    return downloader.download_file(remote_path, local_path)

def upload_navigation_screenshot(local_path: str, userinterface_name: str, screenshot_name: str) -> Dict:
    """
    Upload a navigation screenshot to R2 in the navigation/{userinterface_name} folder.
    
    Args:
        local_path: Local path to the screenshot file
        userinterface_name: Name of the user interface (e.g., 'horizon_android_mobile', 'perseus_360_web')
        screenshot_name: Filename for the screenshot (e.g., 'Home_Screen.jpg')
    
    Returns:
        Dict with success status, url, remote_path, and size
    """
    uploader = get_cloudflare_utils()
    remote_path = f"navigation/{userinterface_name}/{screenshot_name}"
    file_mappings = [{'local_path': local_path, 'remote_path': remote_path}]
    result = uploader.upload_files(file_mappings)
    
    # Return single file format for compatibility
    if result['uploaded_files']:
        return {
            'success': True,
            'url': result['uploaded_files'][0]['url'],
            'remote_path': result['uploaded_files'][0]['remote_path'],
            'size': result['uploaded_files'][0]['size']
        }
    else:
        return {
            'success': False,
            'error': result['failed_uploads'][0]['error'] if result['failed_uploads'] else 'Upload failed'
        }

def upload_heatmap_html(html_content: str, timestamp: str) -> Dict:
    """Upload heatmap HTML to R2 in the heatmaps folder."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create heatmap HTML path: heatmaps/{timestamp}/mosaic.html
        html_path = f"heatmaps/{timestamp}/mosaic.html"
        
        # Create temporary HTML file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write(html_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload HTML file with 14-day signed URL in private mode
            file_mappings = [{'local_path': temp_file_path, 'remote_path': html_path}]
            upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
            
            # Convert to single file result
            if upload_result['uploaded_files']:
                result = {
                    'success': True,
                    'url': upload_result['uploaded_files'][0]['url'],
                    'remote_path': upload_result['uploaded_files'][0]['remote_path']
                }
            else:
                result = {
                    'success': False,
                    'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                }
            
            if result['success']:
                logger.info(f"Uploaded heatmap HTML: {html_path}")
                return {
                    'success': True,
                    'html_path': html_path,
                    'html_url': result['url']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Upload failed')
                }
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Heatmap HTML upload failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def upload_script_report(html_content: str, device_model: str, script_name: str, timestamp: str) -> Dict:
    """Upload script report HTML to R2 in the script-reports folder."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create report folder path: script-reports/{device_model}/{script_name}_{date}_{timestamp}/
        date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
        folder_name = f"{script_name}_{date_str}_{timestamp}"
        report_path = f"script-reports/{device_model}/{folder_name}/report.html"
        
        # Create temporary HTML file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write(html_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload HTML report with 14-day signed URL in private mode
            file_mappings = [{'local_path': temp_file_path, 'remote_path': report_path}]
            upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
            
            # Convert to single file result
            if upload_result['uploaded_files']:
                result = {
                    'success': True,
                    'url': upload_result['uploaded_files'][0]['url'],
                    'remote_path': upload_result['uploaded_files'][0]['remote_path']
                }
            else:
                result = {
                    'success': False,
                    'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                }
            
            if result['success']:
                logger.info(f"Uploaded script report: {report_path}")
                return {
                    'success': True,
                    'report_path': report_path,
                    'report_url': result['url'],
                    'folder_path': f"script-reports/{device_model}/{folder_name}"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Upload failed')
                }
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Script report upload failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def upload_test_video(local_video_path: str, device_model: str, script_name: str, timestamp: str) -> Dict:
    """Upload test execution video MP4 to R2 in the same folder as the script report."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create video path in same folder as script report: script-reports/{device_model}/{script_name}_{date}_{timestamp}/video.mp4
        date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
        folder_name = f"{script_name}_{date_str}_{timestamp}"
        video_path = f"script-reports/{device_model}/{folder_name}/video.mp4"
        
        # Upload video file with proper content type (14-day signed URL in private mode)
        file_mappings = [{
            'local_path': local_video_path,
            'remote_path': video_path,
            'content_type': 'video/mp4'
        }]
        
        upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
        
        # Convert to single file result
        if upload_result['uploaded_files']:
            result = {
                'success': True,
                'url': upload_result['uploaded_files'][0]['url'],
                'remote_path': upload_result['uploaded_files'][0]['remote_path']
            }
            logger.info(f"Uploaded test video: {video_path}")
            return {
                'success': True,
                'video_path': video_path,
                'video_url': result['url']
            }
        else:
            return {
                'success': False,
                'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Video upload failed'
            }
            
    except Exception as e:
        logger.error(f"Failed to upload test video: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def upload_restart_video(local_video_path: str, timestamp: str) -> Dict:
    """Upload restart video MP4 to R2 in the same folder as the report."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create video path in same folder as report: restart-reports/{timestamp}/video.mp4
        video_path = f"restart-reports/{timestamp}/video.mp4"
        
        # Upload video file with proper content type (14-day signed URL in private mode)
        file_mappings = [{
            'local_path': local_video_path,
            'remote_path': video_path,
            'content_type': 'video/mp4'
        }]
        
        upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
        
        # Convert to single file result
        if upload_result['uploaded_files']:
            result = {
                'success': True,
                'url': upload_result['uploaded_files'][0]['url'],
                'remote_path': upload_result['uploaded_files'][0]['remote_path']
            }
            logger.info(f"Uploaded restart video: {video_path}")
            return {
                'success': True,
                'video_path': video_path,
                'video_url': result['url']
            }
        else:
            return {
                'success': False,
                'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Video upload failed'
            }
            
    except Exception as e:
        logger.error(f"Failed to upload restart video: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def upload_restart_report(html_content: str, host_name: str, device_id: str, timestamp: str) -> Dict:
    """Upload restart video report HTML to R2 in the restart-reports folder."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create report folder path: restart-reports/{timestamp}/
        # Use timestamp-based structure like script reports, not device-based
        report_path = f"restart-reports/{timestamp}/restart_video.html"
        
        # Create temporary HTML file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write(html_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload HTML report with 14-day signed URL in private mode
            file_mappings = [{'local_path': temp_file_path, 'remote_path': report_path}]
            upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
            
            # Convert to single file result
            if upload_result['uploaded_files']:
                result = {
                    'success': True,
                    'url': upload_result['uploaded_files'][0]['url'],
                    'remote_path': upload_result['uploaded_files'][0]['remote_path']
                }
            else:
                result = {
                    'success': False,
                    'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                }
            
            if result['success']:
                logger.info(f"Uploaded restart report: {report_path}")
                return {
                    'success': True,
                    'report_path': report_path,
                    'report_url': result['url'],
                    'folder_path': f"restart-reports/{timestamp}"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Upload failed')
                }
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Restart report upload failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def upload_script_logs(log_content: str, device_model: str, script_name: str, timestamp: str) -> Dict:
    """Upload script execution logs to R2."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create report folder path (same as reports for consistency)
        date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
        folder_name = f"{script_name}_{date_str}_{timestamp}"
        remote_path = f"script-logs/{device_model}/{folder_name}/execution.txt"
        
        logger.info(f"Uploading script logs to R2: {remote_path}")
        
        # Create temporary log file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(log_content)
            temp_log_path = temp_file.name
        
        try:
            # Upload with explicit text/plain content type for inline browser display
            # Use 14-day signed URL in private mode (report asset)
            file_mappings = [{
                'local_path': temp_log_path, 
                'remote_path': remote_path,
                'content_type': 'text/plain; charset=utf-8'
            }]
            upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
            
            # Clean up temporary file
            os.unlink(temp_log_path)
            
            if upload_result['success'] and upload_result['uploaded_files']:
                uploaded_file = upload_result['uploaded_files'][0]
                logger.info(f"Uploaded script logs: {uploaded_file['url']}")
                return {
                    'success': True,
                    'url': uploaded_file['url'],
                    'path': remote_path
                }
            else:
                error_msg = 'Upload failed'
                if upload_result['failed_uploads']:
                    error_msg = upload_result['failed_uploads'][0]['error']
                logger.error(f"Script logs upload failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as upload_error:
            # Clean up temporary file on error
            if os.path.exists(temp_log_path):
                os.unlink(temp_log_path)
            raise upload_error
            
    except Exception as e:
        logger.error(f"Script logs upload failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def upload_validation_screenshots(screenshot_paths: list, device_model: str, script_name: str, timestamp: str) -> Dict:
    """Upload validation screenshots to R2 using batch upload."""
    uploader = get_cloudflare_utils()
    
    # Create report folder path
    date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
    folder_name = f"{script_name}_{date_str}_{timestamp}"
    base_folder = f"script-reports/{device_model}/{folder_name}"
    
    # Prepare file mappings for batch upload
    file_mappings = []
    
    for local_path in screenshot_paths:
        # Skip None or missing paths
        if not local_path or not os.path.exists(local_path):
            continue
        
        # Add main screenshot
        filename = os.path.basename(local_path)
        file_mappings.append({
            'local_path': local_path,
            'remote_path': f"{base_folder}/{filename}"
        })
        
        # Add thumbnail if exists
        thumbnail_path = local_path.replace('.jpg', '_thumbnail.jpg')
        if os.path.exists(thumbnail_path):
            thumbnail_filename = os.path.basename(thumbnail_path)
            file_mappings.append({
                'local_path': thumbnail_path,
                'remote_path': f"{base_folder}/{thumbnail_filename}"
            })
    
    if not file_mappings:
        return {
            'success': False,
            'error': 'No valid files found',
            'uploaded_count': 0,
            'failed_count': 0,
            'uploaded_screenshots': [],
            'failed_uploads': []
        }
    
    # Upload all files with report asset URLs (14-day signed URLs in private mode)
    batch_result = uploader.upload_files(file_mappings, for_report_assets=True)
    
    return {
        'success': batch_result['success'],
        'uploaded_count': batch_result['uploaded_count'],
        'failed_count': batch_result['failed_count'],
        'uploaded_screenshots': [
            {
                'local_path': f['local_path'],
                'remote_path': f['remote_path'],
                'url': f['url']
            } for f in batch_result['uploaded_files']
        ],
        'failed_uploads': [
            {
                'path': f['local_path'],
                'error': f['error']
            } for f in batch_result['failed_uploads']
        ],
        'folder_path': base_folder
    }

def get_script_report_folder_url(device_model: str, script_name: str, timestamp: str) -> str:
    """Get base URL for script report folder."""
    uploader = get_cloudflare_utils()
    date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
    folder_name = f"{script_name}_{date_str}_{timestamp}"
    folder_path = f"script-reports/{device_model}/{folder_name}"
    return uploader.get_public_url(folder_path)


def upload_kpi_thumbnails(thumbnails: Dict[str, str], execution_result_id: str, timestamp: str) -> Dict:
    """
    Upload KPI thumbnails to R2.
    
    Args:
        thumbnails: Dict with keys ('before_action', 'after_action', 'before_match', 'match', 'match_original') pointing to local paths
        execution_result_id: Execution result ID
        timestamp: Timestamp string (YYYYMMDDHHMMSS)
        
    Returns:
        Dict with same keys containing R2 URLs
    """
    try:
        uploader = get_cloudflare_utils()
        
        # Create file mappings for batch upload
        file_mappings = []
        for thumb_type, local_path in thumbnails.items():
            if local_path and os.path.exists(local_path):
                logger.info(f"📁 Uploading {thumb_type}: {local_path}")
                remote_path = f"kpi_measurement/{execution_result_id[:8]}/{timestamp}_{thumb_type}.jpg"
                file_mappings.append({
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'content_type': 'image/jpeg'
                })
            else:
                logger.warning(f"⚠️  Skipping {thumb_type}: file not found at {local_path}")
        
        if not file_mappings:
            logger.warning(f"⚠️  No images to upload for {execution_result_id[:8]}")
            return {}
        
        # Batch upload with 14-day signed URLs in private mode
        upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
        
        # Extract URLs and log them
        urls = {}
        for uploaded in upload_result.get('uploaded_files', []):
            remote_path = uploaded['remote_path']
            url = uploaded['url']
            # Extract type from filename (e.g., "20251023120221_before_action.jpg" → "before_action")
            filename = os.path.basename(remote_path)  # Get just the filename
            # Remove timestamp prefix and .jpg extension
            # Format: "20251023120221_before_action.jpg" → "before_action"
            if '_' in filename:
                thumb_type = '_'.join(filename.split('_')[1:]).replace('.jpg', '')
            else:
                thumb_type = 'unknown'
            urls[thumb_type] = url
            logger.info(f"✅ Uploaded {thumb_type}: {url}")
        
        logger.info(f"✓ Uploaded {len(urls)}/{len(thumbnails)} images to R2")
        return urls
        
    except Exception as e:
        logger.error(f"KPI thumbnails upload failed: {str(e)}")
        return {}


def upload_kpi_report(html_content: str, execution_result_id: str, timestamp: str) -> Dict:
    """
    Upload KPI measurement report HTML to R2.
    
    Args:
        html_content: HTML report content
        execution_result_id: Execution result ID
        timestamp: Timestamp string (YYYYMMDDHHMMSS)
        
    Returns:
        Dict with 'success', 'report_url', 'report_path'
    """
    try:
        uploader = get_cloudflare_utils()
        
        # R2 path: kpi_measurement/{exec_result_id_prefix}/{timestamp}.html
        report_path = f"kpi_measurement/{execution_result_id[:8]}/{timestamp}.html"
        
        # Create temporary HTML file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_file.write(html_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload HTML report with 14-day signed URL in private mode
            file_mappings = [{
                'local_path': temp_file_path, 
                'remote_path': report_path,
                'content_type': 'text/html; charset=utf-8'
            }]
            upload_result = uploader.upload_files(file_mappings, for_report_assets=True)
            
            # Convert to single file result
            if upload_result['uploaded_files']:
                result = {
                    'success': True,
                    'url': upload_result['uploaded_files'][0]['url'],
                    'remote_path': upload_result['uploaded_files'][0]['remote_path']
                }
            else:
                result = {
                    'success': False,
                    'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                }
            
            if result['success']:
                logger.info(f"Uploaded KPI report: {report_path}")
                return {
                    'success': True,
                    'report_path': report_path,
                    'report_url': result['url']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Upload failed'),
                    'report_url': ''
                }
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"KPI report upload failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'report_url': ''
        }
