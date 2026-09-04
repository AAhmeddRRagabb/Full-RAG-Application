from typing import Any
from models.system_schemas import RetrievedChunk


from .base_vectordb_client import BaseVectorClient
from clients.vector_dbs.config import (
    VectorDBPGVectorTableColumns,
    VectorDBPGVectorIndexTypes,
    VectorDBDistanceMethods,
    VectorDBPGVectorDistanceMethods
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text
from sqlalchemy.sql import bindparam
from sqlalchemy.dialects.postgresql import JSONB


class PGVectorVDBClient(BaseVectorClient):
    def __init__(
        self,
        db_client          : AsyncSession,
        default_vector_size: int = 384,
        distance_method    : str = None,
        index_threshold    : int = 100
    ):
        super().__init__(
            db_client           = db_client,
            index_threshold     = index_threshold,
            default_vector_size = default_vector_size,
            distance_method     = distance_method
        )

        self.pgvector_table_prefix  = VectorDBPGVectorTableColumns.TABLE_PREFIX.value
        self.table_index_name       = lambda collection_name: f"{self.pgvector_table_prefix}_{collection_name}_vector_idx"

        if self.distance_method == VectorDBDistanceMethods.DOT_DISTANCE.value:
            self.distance_method = VectorDBPGVectorDistanceMethods.DOT.value
        else:
            self.distance_method = VectorDBPGVectorDistanceMethods.COSINE.value


    # --------------------------- Connection ----------------------------------
    async def connect(self) -> bool:
        """
        Returns:
            return a bool indicates whether the connection was successfully created or not.
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    await session.execute(
                        sql_text(
                            "SELECT pg_advisory_xact_lock(747191100)"
                        )
                    )

                    await session.execute(
                        sql_text(
                            "CREATE EXTENSION IF NOT EXISTS vector"
                        )
                    )

        except Exception as e:
            self.logger.error(f"Error While Initiating Vector DB Client: {e}")
            return False

        return True

    async def disconnect(self):
        pass


    # --------------------------- Collections Manipulation ------------------------
    async def is_collection_existed(self, collection_name) -> bool:
        """
        Check if the given collection name exists or not

        Returns:
            if existed -> True   
            if failure or not existed -> False
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
            self.logger.error(f"Error While Checking Collection Existance: {e}")
            return False

        return bool(record)



    async def list_all_collections(self) -> list[str] | None:
        """
        List the collections exist in the database

        Returns:
            if success -> list of collection names 
            if failure -> None
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
            self.logger.error(f"Error While Listing Existing Collections: {e}")
            return None

        return records



    async def get_collection_info(self, collection_name: str) -> dict | None:
        """
        Get info about the given collection name

        Returns:
            ComponentResult:
                if success -> collection info   
                if failure or not existing collection -> None   
        """
        session: AsyncSession

        # check for existance
        if not await self.is_collection_existed(collection_name):
            return None

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
                        self.logger.error(f"Invalid Collection Info: {table_info}")
                        return None
                    
                    # num_records
                    count_stmt = sql_text(f'SELECT COUNT(*) FROM {collection_name}')
                    count_stmt_exc = await session.execute(statement = count_stmt)
                    count = count_stmt_exc.scalar_one_or_none()

                    return {
                        'table_info' : dict(table_info._mapping),
                        'num_records': count
                    }

        except Exception as e:
            self.logger.error(f"Error Retrieving Collection Info: {e}")
            return None



    async def delete_collection(self, collection_name) -> bool:
        """
        Delete the given collection

        Returns:
            a bool indicates whether the collection was deleted successfully or not.
        """

        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    delete_stmt = sql_text(f'DROP TABLE IF EXISTS {collection_name}')

                    await session.execute(delete_stmt, {'collection_name': collection_name})
                    await session.commit()

        except Exception as e:
            self.logger.error(f"Error Deleting Collection: {e}")
            return False

        return True



    async def create_collection(self, collection_name, embedding_size: int | None = None, do_reset = False) -> bool:
        """
        Create a collection with the given name & embedding size

        Returns:
            a bool indicates whether the collection was created successfully or not.
        """

        session: AsyncSession
        embedding_size = embedding_size if embedding_size else self.default_vector_size

        if do_reset:
            _ = await self.delete_collection(collection_name = collection_name)


        # check for existance
        if await self.is_collection_existed(collection_name):
            self.logger.info(f"Collection {collection_name} already exists")
            return True


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
        
                    await session.execute(statement = create_stmt)
                    await session.commit()

        except Exception as e:
            self.logger.error(f"Error Creating Collection: {e}")
            return False
        
        return True

    # --------------------------- Inserting ----------------------------------
    async def insert_one(
        self,
        collection_name: str,
        text           : str,
        record_id      : int,
        vector         : list[float],
        metadata       : dict[str, Any],
    ) -> bool:
        """
        Insert a record into the given collection

        Returns:
            a bool indicates whether the record was inserted successfully or not.
        """



        if not await self.is_collection_existed(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False

        if not record_id and record_id != 0:
            self.logger.error(f"Invalid Record.")
            return False


        session: AsyncSession
        vector = "[" + ",".join([str(v) for v in vector]) + "]" # postgres needs string_list '[1, 2, 3]'

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
            self.logger.error(f"Error Inserting Record: {e}")
            return False


        # Creating IDX
        return await self.create_vector_index(
            collection_name = collection_name, 
            index_type = VectorDBPGVectorIndexTypes.HNSW.value
        )


    async def insert_many(
        self,
        collection_name: str,
        record_ids     : list[int],
        texts          : list[str],
        vectors        : list[list[float]],
        metadata       : list[dict[str, Any]] | None = None,
        batch_size     : int = 50
    ) -> bool:
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
            a bool indicates whether the records were inserted successfully or not.
        """
        if not await self.is_collection_existed(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False

        if len(record_ids) != len(texts) or len(vectors) != len(texts):
            self.logger.error(f"Invalid Records.")
            return False


        if len(metadata) == 0 or not metadata:
            metadata = [None] * len(record_ids)
        
        session: AsyncSession
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
            self.logger.error(f"Error Inserting Records: {e}")
            return False


        # Creating IDX
        return await self.create_vector_index(
            collection_name = collection_name, 
            index_type = VectorDBPGVectorIndexTypes.HNSW.value
        )


    
    async def search_by_vector(
        self,
        collection_name: str,
        vector         : list[float],
        limit          : int = 5
    ) -> list[RetrievedChunk] | None:
        """
        Retrieve the most similar records to vector

        Returns:
            ComponentResult:
                if success -> list of retrieved chunks
                if failure -> None
        """
        if not await self.is_collection_existed(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist.")
            return False

        vector = '[' + ",".join([str(v) for v in vector]) + ']'
        session: AsyncSession

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
                            score = rec.score
                        )

                        for rec in records
                    ]

                    return retrieved_chunks
   
        except Exception as e:
            self.logger.error(f"Error Retrieving: {e}")
            return None

    # ------------------------------- indices functions -------------------------------

    async def is_index_existed(self, collection_name: str) -> bool:
        """
        Check if an index existed

        Returns:
            ComponentResult:
                if exist -> True
                else -> False
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
            self.logger.error(f"Error Checking Index Existance: {e}")
            return False

        return bool(results.scalar_one_or_none())



    async def create_vector_index(self, collection_name: str, index_type: str = VectorDBPGVectorIndexTypes.HNSW.value) -> bool:
        """
        Create a PGVector Index [HNSW | IVFFLAT]

        Returns:
            a bool indicates whether the index was created successfully or not.
        """
        if await self.is_index_existed(collection_name):
            self.logger.info(f"Index for {collection_name} already exists.")
            return True


        session: AsyncSession
        try:
            async with self.db_client() as session:
                async with session.begin():
                    # check num of elements
                    num_records_stmt = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                    num_records_stmt_exe = await session.execute(num_records_stmt)
                    num_records = num_records_stmt_exe.scalar_one()

                    if num_records < self.index_threshold:
                        self.logger.info(f"Num of records is less than the index threshold")
                        return True


                    # create the index
                    self.logger.info(f"Start: Creating index for {collection_name}")
                    index_name = self.table_index_name(collection_name)

                    create_idx_stmt = sql_text(
                        f'CREATE INDEX IF NOT EXISTS {index_name} ON {collection_name} '
                        f'USING {index_type} ({VectorDBPGVectorTableColumns.VECTOR.value} {self.distance_method})'
                    )

                    await session.execute(create_idx_stmt)
                    await session.commit()
                    self.logger.info(f"End: Created index for {collection_name}")

        except Exception as e:
            self.logger.error(f"Error Creating Index: {e}")
            return False

        return True


    # resetting index in case of many data points came -> so I need better clusters
    async def reset_vector_index(self, collection_name: str, index_type: str = VectorDBPGVectorIndexTypes.HNSW.value) -> bool:
        """
        Resetting a PGVector Index [HNSW | IVFFLAT]


        Returns:
            a bool indicates whether the index was resetted successfully or not.
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
            self.logger.error(f"Error Resetting Index: {e}")
            return False
