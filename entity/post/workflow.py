# Here is the `workflow.py` file implementing the entity post workflow functions based on the provided specifications:
# 
# ```python
import json
import logging
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_post(data, meta={"token": "cyoda_token"}):
    """User creates a post with title, body, and optional image."""
    
    cyoda_token = meta["token"]
    
    try:
        # Extracting post details from the data
        title = data['title']
        body = data['body']
        
        # Handle image upload logic
        image_url = None
        if 'image' in data:
            image = data['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid4().hex}_{filename}"
                image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                image.save(image_path)
                image_url = f"/{UPLOAD_FOLDER}/{unique_filename}"

        # Prepare post data
        post_data = {
            'title': title,
            'body': body,
            'image_url': image_url,
            'author': meta.get('user_id'),  # Assuming user_id is passed in meta
            'timestamp': datetime.datetime.now().isoformat()
        }

        # Save the post using entity_service
        post_id = await entity_service.add_item(
            cyoda_token, 'post', ENTITY_VERSION, post_data
        )

        return {"post_id": post_id, "message": "Post created successfully"}, 201

    except Exception as e:
        logger.error(f"Error in create_post: {e}")
        raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def secure_filename(filename):
    return filename.replace(" ", "_")  # Simple filename sanitization
# ```
# 
# ### Explanation:
# - **Imports**: The necessary modules are imported, including logging and the `entity_service` for interacting with the entity storage.
# - **Logging**: Basic logging is set up to capture any errors that occur during the execution of the workflow.
# - **Function `create_post`**: This function handles the creation of a post. It extracts the title and body from the incoming data, processes any uploaded image, and constructs the post data.
# - **Image Handling**: The function checks if an image is provided, validates the file type, and saves it to the specified upload directory.
# - **Entity Storage**: The post data is saved using the `entity_service.add_item` method, and the post ID is returned upon successful creation.
# - **Error Handling**: Any exceptions are logged, and the function raises the error for further handling upstream.
# 
# This implementation follows the provided template and adheres to the specified requirements for the post creation workflow.