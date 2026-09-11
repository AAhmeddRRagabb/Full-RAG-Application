# ------------------------------------------------------
# Implementing the routes related to the NLP workflows
# -------------------------------------------------------

# fastapi utils
from fastapi import APIRouter
from fastapi import status, Request
from fastapi.responses import JSONResponse

# models & schemas
from models.db_objects_models import UserModel
from models.db_objects_models import ChunkModel

from models.enums import ResponsesEnum

from models.request_schemas import PushChunksRequest
from models.request_schemas import RetrievalRequest
from models.request_schemas import GenerationRequest

# controllers
from controllers import NLPController

# helpers
from tqdm.auto import tqdm
import helpers.config as CFG
from helpers.functional import return_server_error, return_bad_request


nlp_router = APIRouter(
    prefix = CFG.NLP_ROUTES_PREFIX,
    tags = ["nlp"]
)


# ----------------------- Add Chunks into Vector DBs # ----------------------- 
@nlp_router.post("/insert_chunks/{user_name}")
async def insert_chunks_into_vector_db(
    request     : Request,
    user_name   : str,
    push_request: PushChunksRequest
) -> JSONResponse:
    """
    Push processed user chunks into the vector database.

    This route mainly does the following:
        - gets or creates the user record.
        - creates the user's vector collection.
        - reads user chunks in pages.
        - embeds and inserts chunks into the vector database.
    """
    # - Setup
    user_model = UserModel(db_client = request.app.db_client)
    chunk_model = ChunkModel(db_client = request.app.db_client)

    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    user = await user_model.get_user_by_name(user_name = user_name)
    if not user:
        return return_bad_request(message = ResponsesEnum.USER_INVALID_NAME.value)

    is_collection_created = await nlp_controller.create_collection(user_name, do_reset = push_request.do_reset)
    if not is_collection_created:
        return return_server_error()


    # - Get Chunks
    page_no = 1
    inserted_items_count = 0

    n_user_chunks = await chunk_model.get_user_chunks_count(user_id = user.user_id),
    if n_user_chunks is None:
        return return_server_error()

    if n_user_chunks == 0:
        return return_bad_request(message = ResponsesEnum.CHUNK_USER_HAS_NO_CHUNKS.value)
    

    pbar = tqdm(total = n_user_chunks, desc = "Vector Indexing", position = 0)


    while True:
        chunks = await chunk_model.get_user_chunks(
            user_id = user.user_id,
            page_no = page_no,
            page_size = PushChunksRequest.page_size
        )

        if len(chunks) == 0 or not chunks:
            break

        chunks_ids = [chunk.chunk_id for chunk in chunks]

        # insert
        is_inserted = await nlp_controller.insert_chunks_into_vector_db(
            user_name = user_name,
            chunks = chunks,
            chunks_ids = chunks_ids,
        )

        if not is_inserted:
            return return_server_error()

        inserted_items_count += len(chunks)
        pbar.update(inserted_items_count)
        page_no += 1


    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.VECTOR_DB_CHUNKS_INSERTION_SUCCESS.value,
            "inserted_items_count": inserted_items_count
        }
    )



# ----------------------- Get Info about Collections ----------------------- #

@nlp_router.get("/collections/{user_name}")
async def get_user_collection_info(
    request  : Request,
    user_name: str
) -> JSONResponse:
    """
    Return vector database collection info for the given user.
    """
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    user_model = UserModel(db_client = request.app.db_client)

    if not user_model.get_user_by_name(user_name = user_name):
        return return_bad_request(message = ResponsesEnum.USER_INVALID_NAME.value)

    collection_info = nlp_controller.get_vector_db_collection_info(user_name = user_name),
    if not collection_info:
        return return_server_error()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "user_collection_info": collection_info
        }
    )


# ----------------------- Retrieving Relevant Chunks ----------------------- #

@nlp_router.post("/retrieve/{user_name}")
async def retrieve_relevant_chunks(
    user_name        : str,
    request          : Request,
    retrieval_request: RetrievalRequest
) -> JSONResponse:
    """
    Retrieve the most relevant vector database chunks for a user query.
    """
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    user_model = UserModel(db_client = request.app.db_client)
    if not user_model.get_user_by_name(user_name = user_name):
        return return_bad_request(message = ResponsesEnum.USER_INVALID_NAME.value)

    relevant_chunks = nlp_controller.search_vector_db_collection(
        user_name = user_name,
        text = retrieval_request.query,
        limit = retrieval_request.limit,
        encode_as_json = True
    )

    if not relevant_chunks or len(relevant_chunks) == 0:
        return return_server_error()


    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "relevant_chunks": relevant_chunks
        }
    )


# ----------------------- Quering the LLM ----------------------- #

@nlp_router.post("/answer_user_query/{user_name}")
async def answer_user_query(
    user_name         : str,
    request           : Request,
    generation_request: GenerationRequest
) -> JSONResponse:
    """
    Answer a user query by retrieving relevant chunks and generating a response.
    """
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client,
        prompt_template_parser = request.app.prompt_template_parser
    )


    user_model = UserModel(db_client = request.app.db_client)
    if not user_model.get_user_by_name(user_name = user_name):
        return return_bad_request(message = ResponsesEnum.USER_INVALID_NAME.value)


    response = await nlp_controller.answer_rag_query(
        user_name       = user_name,
        query           = generation_request.query,
        retrieval_limit = generation_request.limit
    )

    if not response:
        return return_server_error()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            **response
        }
    )
