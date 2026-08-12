from typing import Any
from models.db_schemas import RetrievedChunk


from .base_vectordb_client import BaseVectorClient
from clients.vector_dbs.config import (
    VectorDBPGVectorTableColumns,
    VectorDBPGVectorIndexTypes,
)
from models.enums import ResponsesEnum
from models.system_schemas import ComponentResult

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text
from sqlalchemy.sql import bindparam
from sqlalchemy.dialects.postgresql import JSONB


class PGVectorVDBClient(BaseVectorClient):
    def __init__(
        self,
        db_client: AsyncSession,
        default_vector_size: int = 384,
        distance_method: str = None,
        index_threshold: int = 100
    ):
        super().__init__(
            db_client           = db_client,
            index_threshold     = index_threshold,
            default_vector_size = default_vector_size,
            distance_method     = distance_method
        )

        self.pgvector_table_prefix  = VectorDBPGVectorTableColumns.TABLE_PREFIX.value
        self.table_index_name       = lambda collection_name: f"{self.pgvector_table_prefix}_{collection_name}_vector_idx"

    # --------------------------- Connection ----------------------------------
    async def connect(self):
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    await session.execute(sql_text(
                        "SELECT pg_advisory_xact_lock(747191100)"
                    ))
                    await session.execute(sql_text(
                        "CREATE EXTENSION IF NOT EXISTS vector"
                    ))

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success()

    async def disconnect(self):
        pass


    # --------------------------- Collections Manipulation ------------------------
    async def is_collection_existed(self, collection_name) -> ComponentResult:
        """
        Check if the given collection name exists or not

        Returns:
            ComponentResult:
                if success -> content: whether the collection exists or not
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = sql_text(
                        "SELECT * FROM pg_tables WHERE tablename = :collection_name"
                    )

                    results = await session.execute(
                        stmt, 
                        {"collection_name" : collection_name}
                    )

                    record = results.scalar_one_or_none()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)


        return self._return_success(content = bool(record))



    async def list_all_collections(self) -> ComponentResult:
        """
        List the collections exist in the database

        Returns:
            ComponentResult:
                if success -> content: list of collection names
                if failure -> error & respone message
        """
        session: AsyncSession
        records = []

        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = sql_text(
                        "SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix"
                    )

                    results = await session.execute(
                        stmt,
                        params = {"prefix" : f"{self.pgvector_table_prefix}%"}
                    )

                    records = results.scalars().all()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success(content = records)



    async def get_collection_info(self, collection_name: str) -> ComponentResult:
        """
        Get info about the given collection name

        Returns:
            ComponentResult:
                if success -> content: collection info
                if failure -> error & respone message
        """
        session: AsyncSession

        # check for existance
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.success:
            return self._return_failure(error = is_collection_existed.error, message = is_collection_existed.message)

        if not is_collection_existed.content:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value, message = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value)


        try:
            async with self.db_client() as session:
                async with session.begin():
                    # get table info
                    table_info_stmt = sql_text('''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                    FROM pg_tables
                    WHERE tablename = :collection_name
                    ''')

                    table_info_stmt_exc = await session.execute(
                        statement = table_info_stmt,
                        params = {"collection_name": collection_name}
                    )

                    table_info = table_info_stmt_exc.fetchone()
                    if not table_info:
                        return self._return_failure(error = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

                    # num_records
                    count_stmt = sql_text(f'SELECT COUNT(*) FROM {collection_name}')
                    count_stmt_exc = await session.execute(statement = count_stmt)
                    count = count_stmt_exc.scalar_one_or_none()

                    return self._return_success(
                        content = {
                            'table_info' : dict(table_info._mapping),
                            'num_records': count
                        }
                    )
           
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)



    async def delete_collection(self, collection_name) -> ComponentResult:
        """
        Delete the given collection

        Returns:
            ComponentResult:
                if success -> content: None
                if failure -> error & respone message
        """

        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    delete_stmt = sql_text(f'DROP TABLE IF EXISTS {collection_name}')

                    await session.execute(delete_stmt, {'collection_name': collection_name})
                    await session.commit()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success()



    async def create_collection(self, collection_name, embedding_size: int | None = None, do_reset = False) -> ComponentResult:
        """
        Create a collection with the given name

        Returns:
            ComponentResult:
                if success -> content: None
                if failure -> error & respone message
        """
        session: AsyncSession
        embedding_size = embedding_size if embedding_size else self.default_vector_size

        if do_reset:
            _ = await self.delete_collection(collection_name = collection_name)


        # check for existance
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.success:
            return self._return_failure(error = is_collection_existed.error, message = is_collection_existed.message)

        if not is_collection_existed.content:
            self.logger.info(f"Creating Collection: {collection_name}")

            try:
                async with self.db_client() as session:
                    async with session.begin():
                        create_stmt = sql_text(
                            f'CREATE TABLE {collection_name} ('
                                f'{VectorDBPGVectorTableColumns.ID.value}       bigserial PRIMARY KEY, '
                                f'{VectorDBPGVectorTableColumns.TEXT.value}     text, '
                                f'{VectorDBPGVectorTableColumns.CHUNK_ID.value} integer, '
                                f'{VectorDBPGVectorTableColumns.VECTOR.value}   vector({embedding_size}), '
                                f'{VectorDBPGVectorTableColumns.METADATA.value} jsonb DEFAULT \'{{}}\', '
                                f'FOREIGN KEY ({VectorDBPGVectorTableColumns.CHUNK_ID.value}) REFERENCES chunks(chunk_id) ON DELETE CASCADE'
                            ')'    
                        )
            
                        await session.execute(
                            statement = create_stmt,
                        )

                        await session.commit()
            except Exception as e:
                return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success()



    # --------------------------- Inserting ----------------------------------
    async def insert_one(
        self,
        collection_name: str,
        text: str,
        record_id: int,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> ComponentResult:
        """
        Insert a record into the given collection

        Returns:
            ComponentResult:
                if success -> content: None
                if failure -> error & respone message
        """
        session: AsyncSession
        vector = "[" + ",".join([str(v) for v in vector]) + "]" # postgres needs string_list '[1, 2, 3]'

        is_collection_existed = await self.is_collection_existed(collection_name = collection_name)
        if not is_collection_existed.success:
            return self._return_failure(error = is_collection_existed.error, message = is_collection_existed.message)

        if not is_collection_existed.content:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value, message = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value)

        if not record_id and record_id != 0:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_INVALID_DATA.value, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        try:
            async with self.db_client() as session:
                async with session.begin():

                    insertion_stmt = sql_text(
                        f"INSERT INTO {collection_name}"
                        "("
                            f"{VectorDBPGVectorTableColumns.TEXT.value},"    
                            f"{VectorDBPGVectorTableColumns.CHUNK_ID.value},"    
                            f"{VectorDBPGVectorTableColumns.VECTOR.value},"    
                            f"{VectorDBPGVectorTableColumns.METADATA.value}"    
                        ")"
                        "VALUES ("
                            f"{text}"
                            f"{record_id}"
                            f"{vector}"
                            f"{metadata}"
                        ")"
                    )

                    await session.execute(
                        statement = insertion_stmt
                    )

                    await session.commit()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success()



    async def insert_many(
        self,
        collection_name: str,
        record_ids: list[int],
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
        batch_size: int = 50
    ) -> ComponentResult:
        """
        Insert records into the given collection

        Args:
            collection_name (str) : collection name to insert in
            record_ids      (list): list of record IDs to store
            texts           (list): list of texts to store
            vectors         (list): list of vectors
            metadata        (list): list of metadata
            batch_size      (int) : batch size while inserting

        
        Returns:
            ComponentResult:
                if success -> content: None
                if failure -> error & respone message
        """
        session: AsyncSession

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.success:
            return self._return_failure(error = is_collection_existed.error, message = is_collection_existed.message)

        if not is_collection_existed.content:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value, message = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value)

        if len(record_ids) != len(texts) or len(vectors) != len(texts):
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_INVALID_DATA.value, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)



        if len(metadata) == 0 or not metadata:
            metadata = [None] * len(record_ids)
        
        try:
            async with self.db_client() as session:
                async with session.begin():
                    for i in range(0, len(texts), batch_size):
                        batch_texts      = texts[i : i + batch_size]
                        batch_record_ids = record_ids[i : i + batch_size]
                        batch_vectors    = vectors[i : i + batch_size]
                        batch_metadata   = metadata[i : i + batch_size]

                        values = []

                        for _text, _id, _vector, _metadata in zip(batch_texts, batch_record_ids, batch_vectors, batch_metadata):
                            _vector = "[" + ",".join([str(v) for v in _vector]) + "]"
                            values.append({
                                'text'    : _text,
                                'chunk_id': _id,
                                'vector'  : _vector,
                                'metadata': _metadata
                            })


                        batch_insert_stmt = sql_text(
                            f"INSERT INTO {collection_name}"
                            "("
                                f"{VectorDBPGVectorTableColumns.TEXT.value},"
                                f"{VectorDBPGVectorTableColumns.CHUNK_ID.value},"
                                f"{VectorDBPGVectorTableColumns.VECTOR.value},"
                                f"{VectorDBPGVectorTableColumns.METADATA.value}"
                            ")"
                            "VALUES (:text, :chunk_id, :vector, :metadata)"
                        ).bindparams(bindparam("metadata", type_ = JSONB))

                        await session.execute(
                            batch_insert_stmt,
                            params = values
                        )
                        await session.commit()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success()


    async def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5
    ) -> ComponentResult:
        """
        Insert records into the given collection

        Returns:
            ComponentResult:
                if success -> content: list of retrieved chunks
                if failure -> error & respone message
        """
        session: AsyncSession

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.success:
            return self._return_failure(error = is_collection_existed.error, message = is_collection_existed.message)

        if not is_collection_existed.content:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value, message = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value)


        vector = '[' + ",".join([str(v) for v in vector]) + ']'

        try:
            async with self.db_client() as session:
                async with session.begin():
                    search_stmt = sql_text(
                        'SELECT '
                        f'{VectorDBPGVectorTableColumns.TEXT.value} AS text, '
                        f'1 - ({VectorDBPGVectorTableColumns.VECTOR.value} <=> :vector) AS score '
                        f'FROM {collection_name} '
                        'ORDER BY score DESC '
                        f'LIMIT {limit}'
                    )

                    search_stmt_exe = await session.execute(search_stmt, params = {'vector': vector})

                    records = search_stmt_exe.fetchall()
                    retrieved_chunks = [
                        RetrievedChunk(
                            text  = rec.text,
                            score = rec .score
                        )

                        for rec in records
                    ]

                    return self._return_success(
                        content = retrieved_chunks
                    )
   
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

    # ------------------------------- indices functions -------------------------------

    async def is_index_existed(self, collection_name: str) -> ComponentResult:
        """
        Check if an index existed

        Returns:
            ComponentResult:
                if success -> content: whether the index exists or not
                if failure -> error & respone message
        """
        session: AsyncSession
        index_name = self.table_index_name(collection_name)

        try:
            async with self.db_client() as session:
                async with session.begin():
                    index_check_stmt = sql_text(
                        "SELECT 1"
                        "FROM pg_indexes"
                        f"WHERE tablename = {collection_name}"
                        f"AND   indexname = {index_name}"
                    )
    
                    results = await session.execute(index_check_stmt)

        except Exception as e:
                return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success(bool(results.scalar_one_or_none()))


    async def create_vector_index(self, collection_name: str, index_type: VectorDBPGVectorIndexTypes.HNSW.value) -> ComponentResult:
        """
        Create a PGVector Index [HNSW | IVFFLAT]

        Returns:
            ComponentResult:
                if success -> content: None
                if failure -> error & respone message
        """
        session: AsyncSession

        is_index_existed = await self.is_index_existed(collection_name)
        if is_index_existed.content:
            return self._return_success()

        try:
            async with self.db_client() as session:
                async with session.begin():
                    # check num of elements
                    num_records_stmt = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                    num_records_stmt_exe = await session.execute(num_records_stmt)
                    num_records = num_records_stmt_exe.scalar_one()

                    if num_records < self.index_threshold:
                        return self._return_success()


                    # create the index
                    self.logger(f"Start: Creating index for {collection_name}")
                    index_name = self.table_index_name(collection_name)
                    create_idx_stmt = sql_text(
                        f'CREATE INDEX {index_name} ON {collection_name}'
                        f'USING {index_type} ({VectorDBPGVectorTableColumns.VECTOR.value} {self.distance_method})'
                    )

                    await session.execute(create_idx_stmt)
                    await session.commit()
                    self.logger(f"End: Created index for {collection_name}")

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        return self._return_success()
                

    # resetting index in case of many data points came -> so I need better clusters
    async def reset_vector_index(self, collection_name: str, index_type: VectorDBPGVectorIndexTypes.HNSW.value) -> ComponentResult:
        """
        Resetting a PGVector Index [HNSW | IVFFLAT]

        Returns:
            ComponentResult:
                if success -> content: None
                if failure -> error & respone message
        """
        session: AsyncSession
        index_name = self.table_index_name(collection_name)



        self.logger(f"Start: Resetting index for {collection_name}")
        try:
            async with self.db_client() as session:
                async with session.begin():
                    drop_index_stmt = sql_text(
                        f'DROP INDEX IF EXISTS {index_name}'
                    )

                    await session.execute(drop_index_stmt)
                    await session.commit()

            # re-create
            return await self.create_vector_index(collection_name = collection_name, index_type = index_type)

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value) 
