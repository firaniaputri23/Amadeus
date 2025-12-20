from supabase import create_client
from dotenv import load_dotenv
from typing import Optional, List, Dict
import os


class SupabaseStorageClient:
    """
    A class for interacting with Supabase Storage API.
    
    This class provides methods for managing buckets and files in Supabase Storage.
    """
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize the SupabaseStorageClient.
        
        Args:
            url: Supabase URL. If None, it will be loaded from environment variable.
            key: Supabase key. If None, it will be loaded from environment variable.
        """
        load_dotenv()
        
        self.__supabase_url = url or os.getenv("SUPABASE_URL")
        # self.__supabase_key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.__supabase_key = key or os.getenv("SUPABASE_KEY")
        
        if not self.__supabase_url or not self.__supabase_key:
            raise ValueError("Supabase URL and key must be provided or set as environment variables")
        
        self.__client = create_client(self.__supabase_url, self.__supabase_key)
    
    # Bucket management methods
    def create_bucket(
        self, 
        bucket_name: str, 
        is_public: bool = False, 
        file_size_limit: int = 52_428_800, 
        allowed_mime_types: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a new storage bucket.
        
        Args:
            bucket_name: Name of the bucket
            is_public: Whether the bucket is public
            file_size_limit: Maximum size of files in bytes
            allowed_mime_types: List of allowed MIME types
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.create_bucket(
            bucket_name,
            options={
                "public": is_public,
                "allowed_mime_types": allowed_mime_types,
                "file_size_limit": file_size_limit,
            }
        )
    
    def delete_bucket(self, bucket_name: str) -> Dict:
        """
        Delete a storage bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.delete_bucket(bucket_name)
    
    def empty_bucket(self, bucket_name: str) -> Dict:
        """
        Remove all files from a bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.empty_bucket(bucket_name)
    
    def get_bucket(self, bucket_name: str) -> Dict:
        """
        Get information about a bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.get_bucket(bucket_name)
    
    def list_buckets(self) -> List[Dict]:
        """
        List all buckets.
        
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.list_buckets()
    
    def update_bucket(
        self, 
        bucket_name: str, 
        is_public: bool = False, 
        file_size_limit: int = 52_428_800, 
        allowed_mime_types: Optional[List[str]] = None
    ) -> Dict:
        """
        Update a bucket's configuration.
        
        Args:
            bucket_name: Name of the bucket
            is_public: Whether the bucket is public
            file_size_limit: Maximum size of files in bytes
            allowed_mime_types: List of allowed MIME types
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.update_bucket(
            bucket_name,
            options={
                "public": is_public,
                "allowed_mime_types": allowed_mime_types,
                "file_size_limit": file_size_limit,
            }
        )
    
    def upload_file(self, bucket_name: str, storage_path: str, file, content_type: str) -> Dict:
        """
        Upload a file to a bucket.
        
        Args:
            bucket_name: Name of the bucket
            storage_path: Path where the file will be stored
            file: File content as bytes, or file-like object
            content_type: Content type of the file
            
        Returns:
            Response from the Supabase API
        """
        file_options = {
            "cache-control": "3600",
            "upsert": "false",
            "content-type": content_type
        }
        
        # Jika file adalah bytes, gunakan langsung
        if isinstance(file, bytes):
            return self.__client.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file,  # Meneruskan bytes langsung
                file_options=file_options
            )
        else:
            # Jika file adalah file-like object, coba meneruskannya langsung
            try:
                return self.__client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=file,
                    file_options=file_options
                )
            except Exception as e:
                # Jika gagal, baca isi file dan gunakan bytes
                original_position = file.tell()
                file.seek(0)
                file_content = file.read()
                file.seek(original_position)
                
                return self.__client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=file_content,  # Menggunakan bytes hasil baca
                    file_options=file_options
                )
    
    def replace_file(self, bucket_name: str, storage_path: str, file, content_type: str) -> Dict:
        """
        Replace a file in a bucket.
        
        Args:
            bucket_name: Name of the bucket
            storage_path: Path where the file will be stored
            file: File content as bytes or file-like object
            content_type: Content type of the file
            
        Returns:
            Response from the Supabase API
        """
        file_options = {
            "cache-control": "3600",
            "upsert": "false",
            "content-type": content_type
        }
        
        # Jika file adalah bytes, gunakan langsung
        if isinstance(file, bytes):
            return self.__client.storage.from_(bucket_name).update(
                path=storage_path,
                file=file,  # Meneruskan bytes langsung
                file_options=file_options
            )
        else:
            # Jika file adalah file-like object, coba meneruskannya langsung
            try:
                return self.__client.storage.from_(bucket_name).update(
                    path=storage_path,
                    file=file,
                    file_options=file_options
                )
            except Exception as e:
                # Jika gagal, baca isi file dan gunakan bytes
                original_position = file.tell()
                file.seek(0)
                file_content = file.read()
                file.seek(original_position)
                
                return self.__client.storage.from_(bucket_name).update(
                    path=storage_path,
                    file=file_content,  # Menggunakan bytes hasil baca
                    file_options=file_options
                )
        
    def get_file(self, bucket_name: str, source_path: str):
        """
        Get a file from a bucket.
        
        Args:
            bucket_name: Name of the bucket
            source_path: Path to the source file
            
        Returns:
            File object
        """
        return self.__client.storage.from_(bucket_name).download(source_path)
    
    def download_file(self, bucket_name: str, source_path: str, downloaded_path: str) -> None:
        """
        Download a file from a bucket.
        
        Args:
            bucket_name: Name of the bucket
            source_path: Path to the file in the bucket
            downloaded_path: Path where the file will be saved
        """
        with open(downloaded_path, "wb+") as f:
            response = (self.__client.storage.from_(bucket_name).download(source_path))
            f.write(response)
    
    def list_files(self, bucket_name: str, folder_path: str, 
                  limit: int = 100, offset: int = 0, 
                  sort_column: str = "name", sort_order: str = "desc") -> List[Dict]:
        """
        List files in a bucket folder.
        
        Args:
            bucket_name: Name of the bucket
            folder_path: Path to the folder
            limit: Maximum number of files to return
            offset: Number of files to skip
            sort_column: Column to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).list(
            folder_path,
            {
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": sort_column, "order": sort_order},
            }
        )
    
    def search_files(self, bucket_name: str, folder_path: str, search_key: str,
                    limit: int = 100, offset: int = 0, 
                    sort_column: str = "name", sort_order: str = "desc") -> List[Dict]:
        """
        Search for files in a bucket folder.
        
        Args:
            bucket_name: Name of the bucket
            folder_path: Path to the folder
            search_key: Search query
            limit: Maximum number of files to return
            offset: Number of files to skip
            sort_column: Column to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).list(
            folder_path,
            {
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": sort_column, "order": sort_order},
                "search": search_key,
            }
        )
    
    def move_file(self, bucket_name: str, original_path: str, target_path: str) -> Dict:
        """
        Move a file in a bucket.
        
        Args:
            bucket_name: Name of the bucket
            original_path: Current path of the file
            target_path: New path for the file
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).move(original_path, target_path)
    
    def delete_files(self, bucket_name: str, files_path: List[str]) -> Dict:
        """
        Delete files from a bucket.
        
        Args:
            bucket_name: Name of the bucket
            files_path: List of paths to files to delete
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).remove(files_path)
    
    def copy_file(self, bucket_name: str, source_path: str, target_path: str) -> Dict:
        """
        Copy a file in a bucket.
        
        Args:
            bucket_name: Name of the bucket
            source_path: Path to the source file
            target_path: Path for the copied file
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).copy(source_path, target_path)
    
    # URL generation methods
    def create_download_url(self, bucket_name: str, storage_path: str, expired_time_minutes: int = 5) -> Dict:
        """
        Create a signed URL for downloading a file.
        
        Args:
            bucket_name: Name of the bucket
            storage_path: Path to the file
            expired_time_minutes: Time until the URL expires, in minutes
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).create_signed_url(
            storage_path, 
            expired_time_minutes * 60, 
            {"download": True}
        )
    
    def create_view_url(self, bucket_name: str, storage_path: str, expired_time_minutes: int = 5) -> Dict:
        """
        Create a signed URL for viewing a file.
        
        Args:
            bucket_name: Name of the bucket
            storage_path: Path to the file
            expired_time_minutes: Time until the URL expires, in minutes
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).create_signed_url(
            storage_path, 
            expired_time_minutes * 60
        )
    
    def create_view_urls(self, bucket_name: str, storage_paths: List[str], expired_time_minutes: int = 5) -> List[Dict]:
        """
        Create signed URLs for viewing multiple files.
        
        Args:
            bucket_name: Name of the bucket
            storage_paths: List of paths to files
            expired_time_minutes: Time until the URLs expire, in minutes
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).create_signed_urls(
            storage_paths, 
            expired_time_minutes * 60
        )
    
    def create_download_urls(self, bucket_name: str, storage_paths: List[str], expired_time_minutes: int = 5) -> List[Dict]:
        """
        Create signed URLs for downloading multiple files.
        
        Args:
            bucket_name: Name of the bucket
            storage_paths: List of paths to files
            expired_time_minutes: Time until the URLs expire, in minutes
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).create_signed_urls(
            storage_paths, 
            expired_time_minutes * 60,
            {"download": True}
        )
    
    def create_upload_url(self, bucket_name: str, storage_path: str) -> Dict:
        """
        Create a signed URL for uploading a file.
        
        Args:
            bucket_name: Name of the bucket
            storage_path: Path for the file
            
        Returns:
            Response from the Supabase API
        """
        return self.__client.storage.from_(bucket_name).create_signed_upload_url(storage_path)
    
    def upload_via_url(self, bucket_name: str, source_path: str, storage_path: str, token_upload: str) -> Dict:
        """
        Upload a file using a signed URL.
        
        Args:
            bucket_name: Name of the bucket
            source_path: Path to the source file
            storage_path: Path for the file in the bucket
            token_upload: Upload token
            
        Returns:
            Response from the Supabase API
        """
        with open(source_path, "rb") as f:
            return self.__client.storage.from_(bucket_name).upload_to_signed_url(
                path=storage_path,
                token=token_upload,
                file=f,
            )
    
    def get_public_url(self, bucket_name: str, storage_path: str) -> str:
        """
        Get the public URL of a file.
        
        Args:
            bucket_name: Name of the bucket
            storage_path: Path to the file
            
        Returns:
            Public URL of the file
        """
        return self.__client.storage.from_(bucket_name).get_public_url(storage_path)

    def run_rpc(self, function_name: str, params: Dict):
        """
        Run RPC.
        
        Args:
            function_name: Name of the function
            params: params of the function
            
        Returns:
            Result based on each function
        """
        return self.__client.rpc(fn=function_name, params=params)
    
    def insert_to_tabel(self, table_name, data):
        """
        Insert new data into a specified table.

        Args:
            table_name (str): The name of the table to insert data into.
            data (dict or list of dict): The data to insert.

        Returns:
            None
        """
        self.__client.table(table_name).insert(data).execute()


    def update_to_tabel(self, table_name, column_id, id, data):
        """
        Update existing data in a specified table by matching a column ID.

        Args:
            table_name (str): The name of the table to update.
            column_id (str): The name of the column used for filtering (e.g., "user_id").
            id (Any): The value of the column to match.
            data (dict): The updated data to apply.

        Returns:
            None
        """
        self.__client.table(table_name).update(data).eq(column_id, id).execute()


# Example usage
if __name__ == "__main__":
    # Initialize the client
    storage_client = SupabaseStorageClient()
    
    # Example paths
    example_article = r"data\example\article_journal.pdf"
    example_cv = r"data\example\curriculum_vitae.pdf"
    downloaded_path = r"data\download\download.pdf"

    # Example usage (commented out)
    """
    # Bucket operations
    print(storage_client.create_bucket("users-files", is_public=False))
    print(storage_client.list_buckets())
    print(storage_client.get_bucket("users-files"))
    print(storage_client.update_bucket("users-files", is_public=True))
    
    # File operations
    print(storage_client.upload_file("users-files", "public/article_journal.pdf", example_article))
    print(storage_client.upload_file("users-files", "public/cv.pdf", example_cv))
    print(storage_client.list_files("users-files", "public"))
    print(storage_client.search_files("users-files", "public", "article"))
    
    # File management
    print(storage_client.move_file("users-files", "public/article_journal.pdf", "private/moved_article.pdf"))
    print(storage_client.copy_file("users-files", "private/moved_article.pdf", "public/copied_article.pdf"))
    print(storage_client.delete_files("users-files", ["public/copied_article.pdf"]))
    
    # URL operations
    print(storage_client.create_download_url("users-files", "public/cv.pdf"))
    print(storage_client.create_view_url("users-files", "public/cv.pdf"))
    print(storage_client.get_public_url("users-files", "public/cv.pdf"))
    
    # Cleanup
    print(storage_client.empty_bucket("users-files"))
    print(storage_client.delete_bucket("users-files"))
    """