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
from helpers.functional import parse_component_result, FAILURE, return_bad_request


nlp_router = APIRouter(
    prefix = CFG.NLP_ROUTES_PREFIX,
    tags = ["nlp"]
)


# --- Add Chunks into Vector DBs
@nlp_router.post("/push/{user_name}")
async def push_chunks_into_vector_db(
    request: Request,
    user_name: str,
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
    # setup
    user_model = UserModel(db_client = request.app.db_client)
    chunk_model = ChunkModel(db_client = request.app.db_client)

    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    flag, user_or_failure = parse_component_result(
        await user_model.get_user_or_insert_it(user_name = user_name),
        error_message = "Error while accessing the user"
    )
    
    if flag == FAILURE:
        return user_or_failure

    flag, creation_or_failure = parse_component_result(
        await nlp_controller.create_collection(user_name, do_reset = push_request.do_reset),
        error_message = "Error while creating collection"
    )
    if flag == FAILURE:
        return creation_or_failure

    # get chunks to store
    page_no = 1
    inserted_items_count = 0

    flag, total_chunks_or_failure = parse_component_result(
        await chunk_model.get_total_chunks_per_user(user_id = user_or_failure.user_id),
        error_message = "Error while Accessing N.Chun;s"
    )

    if flag == FAILURE:
        return total_chunks_or_failure

    pbar = tqdm(total = total_chunks_or_failure, desc="Vector Indexing", position=0)

    while True:
        flag, chunks_or_failure = parse_component_result(
            await chunk_model.get_user_chunks(
                user_id = user_or_failure.user_id,
                page_no = page_no,
            ),
            error_message = "Error while accessing user chunks"
        )
        if flag == FAILURE:
            return chunks_or_failure

        if not chunks_or_failure or len(chunks_or_failure) == 0:
            break

        chunks_ids = [chunk.chunk_id for chunk in chunks_or_failure]

        # insert
        flag, insertion_or_failure = parse_component_result(
            await nlp_controller.insert_into_vector_db(
                user_name = user_name,
                chunks = chunks_or_failure,
                chunks_ids = chunks_ids,
            ),
            error_message = "Error while inserting chunks"
        )
        if flag == FAILURE:
            return insertion_or_failure

        inserted_items_count += len(chunks_or_failure)
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


@nlp_router.get("/collections/{user_name}")
async def get_user_collection(
    request: Request,
    user_name: str
) -> JSONResponse:
    """
    Return vector database collection info for the given user.
    """
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    flag, collection_info_or_failure = parse_component_result(
        await nlp_controller.get_vector_db_collection_info(user_name = user_name),
        error_message = "Error Retrieving Collection Info"
    )
    if flag == FAILURE:
        return collection_info_or_failure

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "user_collection_info": collection_info_or_failure
        }
    )


# ---- Retrieve
@nlp_router.post("/retrieve/{user_name}")
async def retrieve_relevant_chunks(
    user_name: str,
    request: Request,
    retrieval_request: RetrievalRequest
) -> JSONResponse:
    """
    Retrieve the most relevant vector database chunks for a user query.
    """
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    flag, chunks_or_failure = parse_component_result(
        await nlp_controller.search_vector_db_collection(
            user_name = user_name,
            text = retrieval_request.query,
            limit = retrieval_request.limit,
            encode_as_json = True
        ),
        error_message = "Error While Retrieving"
    )
    if flag == FAILURE:
        return chunks_or_failure

    if not chunks_or_failure or len(chunks_or_failure) == 0:
        return return_bad_request(
            message = f"{ResponsesEnum.VECTOR_DB_INNER_ERROR.value}"
        )

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "relevant_chunks": chunks_or_failure
        }
    )


# --- Generation
@nlp_router.post("/answer_user_query/{user_name}")
async def answer_user_query(
    user_name: str,
    request: Request,
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

    flag, answer_or_failure = parse_component_result(
        await nlp_controller.answer_rag_query(
            user_name = user_name,
            query = generation_request.query,
            retrieval_limit = generation_request.limit
        ),
        error_message = "Error While Generating"
    )
    if flag == FAILURE:
        return answer_or_failure

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            **answer_or_failure
        }
    )
