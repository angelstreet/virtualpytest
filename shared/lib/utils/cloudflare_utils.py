#!/usr/bin/env python3

"""
Cloudflare R2 Utilities for VirtualPyTest Resources

Utilities for uploading and downloading files from Cloudflare R2 with public access.

Folder Structure:
- reference/{model}/{image_name}     # Reference images (public access)
- navigation/{model}/{screenshot_name} # Navigation screenshots (public access)
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[@cloudflare_utils:%(funcName)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class CloudflareUtils:
    """
    Singleton Cloudflare R2 utility for VirtualPyTest resources.
    Upload and download files and get signed URLs.
    
    This class implements the singleton pattern to ensure only one instance
    exists throughout the application lifecycle, avoiding multiple S3 client
    initializations.
    
    Configuration:
    - Copy shared/env.example to shared/.env and configure your credentials
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
        
        # Load environment variables from .env file
        self._load_environment()
        
        # Use 'virtualpytest' as bucket name (boto3 requires valid bucket name)
        self.bucket_name = 'virtualpytest'
        self.s3_client = self._init_s3_client()
        self._initialized = True
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        try:
            from dotenv import load_dotenv
            import os
            
            # Try to find .env file in shared directory
            current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/lib/utils
            shared_dir = os.path.dirname(os.path.dirname(current_dir))  # /shared
            env_path = os.path.join(shared_dir, '.env')
            
            if os.path.exists(env_path):
                logger.info(f"Loading environment from: {env_path}")
                load_dotenv(env_path)
            else:
                logger.warning(f"No .env file found at: {env_path}")
                logger.info("Copy shared/env.example to shared/.env and configure your credentials")
            
            # Log what we found (without showing sensitive values)
            logger.info(f"CLOUDFLARE_R2_ENDPOINT: {'SET' if os.environ.get('CLOUDFLARE_R2_ENDPOINT') else 'NOT_SET'}")
            logger.info(f"CLOUDFLARE_R2_ACCESS_KEY_ID: {'SET' if os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID') else 'NOT_SET'}")
            logger.info(f"CLOUDFLARE_R2_SECRET_ACCESS_KEY: {'SET' if os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY') else 'NOT_SET'}")
            logger.info(f"CLOUDFLARE_R2_PUBLIC_URL: {'SET' if os.environ.get('CLOUDFLARE_R2_PUBLIC_URL') else 'NOT_SET'}")
            
        except ImportError:
            logger.warning("python-dotenv not available, relying on system environment variables")
        except Exception as e:
            logger.error(f"Error loading environment: {e}")
    
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
    
    def upload_files(self, file_mappings: List[Dict], max_workers: int = 10) -> Dict:
        """
        Upload files concurrently.
        
        Args:
            file_mappings: List of dicts with 'local_path' and 'remote_path' keys
            max_workers: Maximum number of concurrent upload threads
            
        Returns:
            Dict with upload results
        """
        uploaded_files = []
        failed_uploads = []
        
        def upload_single_file(mapping):
            local_path = mapping['local_path']
            remote_path = mapping['remote_path']
            
            try:
                if not os.path.exists(local_path):
                    return {
                        'success': False,
                        'local_path': local_path,
                        'remote_path': remote_path,
                        'error': f"File not found: {local_path}"
                    }
                
                content_type, _ = guess_type(local_path)
                if not content_type:
                    content_type = 'application/octet-stream'
                
                with open(local_path, 'rb') as f:
                    self.s3_client.upload_fileobj(
                        f,
                        self.bucket_name,
                        remote_path,
                        ExtraArgs={'ContentType': content_type}
                    )
                
                file_url = self.get_public_url(remote_path)
                
                return {
                    'success': True,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'url': file_url,
                    'size': os.path.getsize(local_path)
                }
                
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
                else:
                    failed_uploads.append(result)
        
        return {
            'success': len(failed_uploads) == 0,
            'uploaded_count': len(uploaded_files),
            'failed_count': len(failed_uploads),
            'uploaded_files': uploaded_files,
            'failed_uploads': failed_uploads
        }
    
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

def upload_reference_image(local_path: str, model: str, image_name: str) -> Dict:
    """Upload a reference image to R2 in the reference-images/{model} folder."""
    uploader = get_cloudflare_utils()
    remote_path = f"reference-images/{model}/{image_name}"
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

def download_reference_image(model: str, image_name: str, local_path: str) -> Dict:
    """Download a reference image from R2 in the reference-images/{model} folder."""
    downloader = get_cloudflare_utils()
    remote_path = f"reference-images/{model}/{image_name}"
    return downloader.download_file(remote_path, local_path)

def upload_navigation_screenshot(local_path: str, model: str, screenshot_name: str) -> Dict:
    """Upload a navigation screenshot to R2 in the navigation/{model} folder."""
    uploader = get_cloudflare_utils()
    remote_path = f"navigation/{model}/{screenshot_name}"
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

def upload_script_logs(log_content: str, device_model: str, script_name: str, timestamp: str) -> Dict:
    """Upload script execution logs to R2."""
    try:
        uploader = get_cloudflare_utils()
        
        # Create report folder path (same as reports for consistency)
        date_str = timestamp[:8]  # YYYYMMDD from YYYYMMDDHHMMSS
        folder_name = f"{script_name}_{date_str}_{timestamp}"
        remote_path = f"script-logs/{device_model}/{folder_name}/execution.log"
        
        logger.info(f"Uploading script logs to R2: {remote_path}")
        
        # Create temporary log file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as temp_file:
            temp_file.write(log_content)
            temp_log_path = temp_file.name
        
        try:
            # Upload log file
            file_mappings = [{'local_path': temp_log_path, 'remote_path': remote_path}]
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
        if not os.path.exists(local_path):
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
