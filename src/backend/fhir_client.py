import requests
from config import MAX_HOSPITAL_SERVER_RETRIES
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .log import logger

load_dotenv()

# Configuration
HOSPITAL_SERVER_TYPE = "local"
FHIR_PORT = 8080
if HOSPITAL_SERVER_TYPE == "local":
    base_url = f"http://localhost:{FHIR_PORT}/fhir/"
    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Content-Type": "application/fhir+json",
    }
    logger.info("Using local FHIR server.")

else:
    raise ValueError(f"Invalid hospital server type: {HOSPITAL_SERVER_TYPE}")


max_retries = MAX_HOSPITAL_SERVER_RETRIES
# os.chdir(os.path.dirname(os.path.abspath(__file__)))


def create_fhir_session(
    retries: int = max_retries,
    backoff_factor: float = 1.0,
    status_forcelist: list = [500, 502, 503, 504],
    allowed_methods: list = ["POST", "GET", "PUT"],
) -> requests.Session:
    """
    Creates and configures a requests.Session with retry logic.

    Args:
        retries (int): Total number of retry attempts.
        backoff_factor (float): A backoff factor to apply between attempts.
        status_forcelist (list): A set of HTTP status codes that we should force a retry on.
        allowed_methods (list): HTTP methods to retry.

    Returns:
        requests.Session: Configured session object.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    logger.info("Succesfully launched FHIR session.")
    return session


def post_fhir_resource(resource, headers, base_url=base_url, session=None):
    """
    Posts a FHIR resource to the server with enhanced error handling and logging.

    Args:
        resource: The FHIR resource to be posted.
        headers: The headers to be used in the HTTP request.
        base_url: The base URL of the FHIR server. Defaults to the global base_url.

    Returns:
        str or None: The ID of the created resource if successful, None otherwise.

    Raises:
        Logs various exceptions that may occur during the request.
    """
    resource_type = resource.resource_type
    payload = resource.json()
    resource_id = resource.id

    if resource_id and not resource.meta:
        # Use POST to create new resources without client-assigned IDs
        url = f"{base_url}{resource_type}/"
        method = "POST"
    elif resource_id:
        # Use PUT to update existing resources
        url = f"{base_url}{resource_type}/{resource_id}"
        method = "PUT"
    else:
        # Use POST to create new resources
        url = f"{base_url}{resource_type}/"
        method = "POST"

    try:
        response = session.request(
            method, url, headers=headers, data=payload, timeout=10
        )
        response.raise_for_status()
        response_data = response.json()

        if method == "POST":
            # Get the resource ID from the response
            resource_id = (
                response_data.get("id")
                or response.headers.get("Location", "").split("/")[-1]
            )
            logger.info(f"{resource_type} created successfully with ID: {resource_id}")
            return resource_id
        else:
            logger.info(f"{resource_type} updated successfully with ID: {resource_id}")
            return resource_id

    except requests.exceptions.HTTPError as http_err:
        logger.error(
            f"HTTP error occurred while posting {resource_type}: {http_err} - Response: {response.text}"
        )
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(
            f"Connection error occurred while posting {resource_type}: {conn_err}"
        )
    except requests.exceptions.Timeout as timeout_err:
        logger.error(
            f"Timeout error occurred while posting {resource_type}: {timeout_err}"
        )
    except requests.exceptions.RequestException as req_err:
        logger.error(f"General error occurred while posting {resource_type}: {req_err}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return None


session = create_fhir_session()
