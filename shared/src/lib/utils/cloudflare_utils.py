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
                raise ValueError("Missing required Cloudflare R2 environment variables")
            
            logger.info("Initializing S3 client for Cloudflare R2")
            logger.info(f"Using endpoint: {endpoint_url}")
            logger.info(f"Using bucket: {self.bucket_name}")
            
            return boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4')
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Cloudflare R2 client: {str(e)}")
            raise
    
    def upload_files(self, file_mappings: List[Dict], max_workers: int = 10, auto_delete_cold: bool = True) -> Dict:
        """
        Upload files concurrently.
        
        Args:
            file_mappings: List of dicts with 'local_path' and 'remote_path' keys
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
            Dict with success status and local file path
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file using bucket name
            self.s3_client.download_file(
                self.bucket_name,
                remote_path,
                local_path
            )
            
            logger.info(f"Downloaded: {remote_path} -> {local_path}")
            
            return {
                'success': True,
                'remote_path': remote_path,
                'local_path': local_path,
                'size': os.path.getsize(local_path)
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.error(f"File not found in R2: {remote_path}")
                return {'success': False, 'error': f"File not found in R2: {remote_path}"}
            else:
                logger.error(f"Download failed: {str(e)}")
                return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
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
    
    def get_public_url(self, remote_path: str) -> str:
        """
        Get a public URL for a file in R2.
        
        Args:
            remote_path: Path in R2
            
        Returns:
            Public URL string
        """
        public_url_base = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', '')
        if not public_url_base:
            logger.error("CLOUDFLARE_R2_PUBLIC_URL environment variable not set")
            return ""
        
        # Remove trailing slash if present and add the remote path
        base_url = public_url_base.rstrip('/')
        return f"{base_url}/{remote_path}"
    
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
            # Upload HTML file
            file_mappings = [{'local_path': temp_file_path, 'remote_path': html_path}]
            upload_result = uploader.upload_files(file_mappings)
            
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
            # Upload HTML report
            file_mappings = [{'local_path': temp_file_path, 'remote_path': report_path}]
            upload_result = uploader.upload_files(file_mappings)
            
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
        
        # Upload video file with proper content type
        file_mappings = [{
            'local_path': local_video_path,
            'remote_path': video_path,
            'content_type': 'video/mp4'
        }]
        
        upload_result = uploader.upload_files(file_mappings)
        
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
        
        # Upload video file with proper content type
        file_mappings = [{
            'local_path': local_video_path,
            'remote_path': video_path,
            'content_type': 'video/mp4'
        }]
        
        upload_result = uploader.upload_files(file_mappings)
        
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
            # Upload HTML report
            file_mappings = [{'local_path': temp_file_path, 'remote_path': report_path}]
            upload_result = uploader.upload_files(file_mappings)
            
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
            file_mappings = [{
                'local_path': temp_log_path, 
                'remote_path': remote_path,
                'content_type': 'text/plain; charset=utf-8'
            }]
            upload_result = uploader.upload_files(file_mappings)
            
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
    
    # Upload all files
    batch_result = uploader.upload_files(file_mappings)
    
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
        
        # Batch upload
        upload_result = uploader.upload_files(file_mappings)
        
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
            # Upload HTML report
            file_mappings = [{
                'local_path': temp_file_path, 
                'remote_path': report_path,
                'content_type': 'text/html; charset=utf-8'
            }]
            upload_result = uploader.upload_files(file_mappings)
            
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
