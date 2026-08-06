from typing import Any
from .vector_db_interface import VectorDBInterface
from models.db_schemas import RetrievedChunk
from stores.vector_dbs.dbs_enums.distance_methods import (
    PGVectorDistanceMethodsEnum,
    DistanceMethodsEnum,
    PGVectorTableColumnsEnum,
    PGVectorIndexTypesEnum
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text

import logging

class PGVectorProvider(VectorDBInterface):
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

        self.logger                 = logging.getLogger('uvicorn')
        self.pgvector_table_prefix  = PGVectorTableColumnsEnum.__TABLE_PREFIX.value
        self.table_index_name       = lambda collection_name: f"{self.pgvector_table_prefix}_{collection_name}_vector_idx"

    async def connect(self):
        session: AsyncSession

        async with self.db_client() as session:
            async with session.begin():
                await session.execute(sql_text(
                    "CREATE EXTENSION IF NOT EXISTS vector"
                ))

            await session.commit()


    async def disconnect(self):
        pass



    async def is_collection_existed(self, collection_name):
        session: AsyncSession
        record = None

        async with self.db_client() as session:
            async with session.begin():
                stmt = sql_text(
                    "SELECT * FROM pg_tables WHERE tablename = :collection_name"
                )

                results = await session.execute(
                    stmt, 
                    {"collection_name" : collection_name}
                )

                record = results.select_one_or_none()

        return record


    async def list_all_collections(self) -> list[str]:
        session: AsyncSession
        records = []

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

        return records


    async def get_collection_info(self, collection_name: str) -> dict:
        session: AsyncSession

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
                    params = {'collection_name': collection_name}
                )

                table_info = table_info_stmt_exc.fetchone()
                if not table_info:
                    return None

                # num_records
                count_stmt = sql_text('SELECT COUNT(*) FROM :collection_name')
                count_stmt_exc = await session.execute(statement = count_stmt, params = {'collection_name': collection_name})
                count = count_stmt_exc.scalar_one_or_none()


                return {
                    'table_info' : dict(table_info),
                    'num_records': count
                }



    async def delete_collection(self, collection_name):
        session: AsyncSession

        async with self.db_client() as session:
            async with session.begin():
                delete_stmt = sql_text('DROP TABLE IF EXISTS :collection_name')

                await session.execute(delete_stmt, {'collection_name': collection_name})
                await session.commit()

        return True



    async def create_collection(self, collection_name, embedding_size: int | None = None, do_reset = False):
        if do_reset:
            _ = await self.delete_collection(collection_name = collection_name)

        session: AsyncSession
        embedding_size = embedding_size if embedding_size else self.default_vector_size

        is_collection_existed = await self.is_collection_existed(collection_name = collection_name)
        if not is_collection_existed:
            self.logger.info(f"Creating Collection: {collection_name}")

            async with self.db_client() as session:
                async with session.begin():
                    create_stmt = sql_text(
                        'CREATE TABLE :collection_name'
                        f'{PGVectorTableColumnsEnum.ID.value}       bigserial PRIMART KEY, '
                        f'{PGVectorTableColumnsEnum.TEXT.value}     text, '
                        f'{PGVectorTableColumnsEnum.CHUNK_ID.value} integer, '
                        f'{PGVectorTableColumnsEnum.VECTOR.value}   vector({embedding_size}), '
                        f'{PGVectorTableColumnsEnum.METADATA.value} jsonb DEFAULT \'{{}}\', '
                        f'FOREIGN KEY ({PGVectorTableColumnsEnum.CHUNK_ID.value}) REFERENCES chunks(chunk_id)'    
                    )
        
                    await session.execute(
                        statement = create_stmt,
                        params = {'collection_name': f"{self.pgvector_table_prefix}_{collection_name}"}
                    )

                    await session.commit()

            return True

        return False



    async def insert_one(
        self,
        collection_name: str,
        text: str,
        record_id: int,
        vector: list[float],
        metadata: dict[str, Any],
    ):

        if not self.is_collection_existed(collection_name):
            self.logger.error("Collection does not exist")
            return False

        if not record_id and record_id != 0:
            self.logger.error("Cannot Insert without record id")
            return False


        session: AsyncSession

        vector = "[" + ",".join([str(v) for v in vector]) + "]" # postgres needs string_list '[1, 2, 3]'

        async with self.db_client() as session:
            async with session.begin():

                insertion_stmt = sql_text(
                    f"INSERT INTO {collection_name}"
                    "("
                        f"{PGVectorTableColumnsEnum.TEXT.value},"    
                        f"{PGVectorTableColumnsEnum.CHUNK_ID.value},"    
                        f"{PGVectorTableColumnsEnum.VECTOR.value},"    
                        f"{PGVectorTableColumnsEnum.METADATA.value}"    
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

        return True



    async def insert_many(
        self,
        collection_name: str,
        record_ids: list[int],
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
        batch_size: int = 50
    ):

        if not self.is_collection_existed(collection_name):
            self.logger.error("Collection does not exist")
            return False

        if len(record_ids) != len(texts) or len(vectors) != len(texts):
            self.logger.error("Invalid Data")
            return False

        if len(metadata) == 0 or not metadata:
            metadata = [None] * len(record_ids)


        session: AsyncSession

        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_texts      = texts[i : i + batch_size]
                    batch_record_ids = record_ids[i : i + batch_size]
                    batch_vectors    = vectors[i : i + batch_size]
                    batch_metadata   = metadata[i : i + batch_size]

                    values = []

                    for _text, _id, _vector, _metadata in zip(batch_texts, batch_record_ids, batch_vectors, batch_metadata):
                        values.append({
                            'text'    : _text,
                            'chunk_id': _id,
                            'vector'  : _vector,
                            'metadata': _metadata
                        })


                    batch_insert_stmt = sql_text(
                        f"INSERT INTO {collection_name}"
                        "("
                            f"{PGVectorTableColumnsEnum.TEXT.value}"
                            f"{PGVectorTableColumnsEnum.CHUNK_ID.value}"
                            f"{PGVectorTableColumnsEnum.VECTOR.value}"
                            f"{PGVectorTableColumnsEnum.METADATA.value}"
                        ")"
                        "VALUES (:text, :chunk_id, :vector, :metadata)"
                    )

                    await session.execute(
                        batch_insert_stmt,
                        params = values
                    )

                    await session.commit()

        return True



    async def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5
    ) -> RetrievedChunk:

        if not self.is_collection_existed(collection_name):
            self.logger.error("Collection does not exist")
            return False


        vector = '[' + ",".join([str(v) for v in vector]) + ']'

        session: AsyncSession
        async with self.db_client() as session:
            async with session.begin():
                search_stmt = sql_text(
                    'SELECT'
                        f'{PGVectorTableColumnsEnum.TEXT.value} as text,'
                        f'1 - {PGVectorTableColumnsEnum.VECTOR.value} <=> {vector} as score'
                    f'FROM {collection_name}'
                    'ORDER BY score desc'
                    f'LIMIT {limit}'
                )

                search_stmt_exe = await session.execute(search_stmt)

                records = search_stmt_exe.fetchall()


                return [
                    RetrievedChunk(
                        text  = rec.text,
                        score = rec .score
                    )

                    for rec in records
                ]

    # ---------------------------------------------
    # indices functions

    async def is_index_existed(self, collection_name: str):
        index_name = self.table_index_name(collection_name)

        session: AsyncSession
        async with self.db_client() as session:
            async with session.begin():
                index_check_stmt = sql_text(
                    "SELECT 1"
                    "FROM pg_indexes"
                    f"WHERE tablename = {collection_name}"
                    f"AND   indexname = {index_name}"
                )

                results = await session.execute(index_check_stmt)

                return bool(results.scalar_one_or_none())



    async def create_vector_index(self, collection_name: str, index_type: PGVectorIndexTypesEnum.HNSW.value):
        """
        Args:
            index_type: hsnw or ivfflat
        """

        if self.is_index_existed(collection_name):
            return False

        session: AsyncSession
        async with self.db_client() as session:
            async with session.begin():
                # check num of elements
                num_records_stmt = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                num_records_stmt_exe = await session.execute(num_records_stmt)
                num_records = num_records_stmt_exe.scalar_one()

                if num_records < self.index_threshold:
                    return False


                # create the index
                self.logger(f"Start: Creating index for {collection_name}")
                index_name = self.table_index_name(collection_name)
                create_idx_stmt = sql_text(
                    f'CREATE INDEX {index_name} ON {collection_name}'
                    f'USING {index_type} ({PGVectorTableColumnsEnum.VECTOR.value} {self.distance_method})'
                )

                await session.execute(create_idx_stmt)
                await session.commit()
                self.logger(f"End: Created index for {collection_name}")

                

    # resetting index in case of many data points came -> so I need better clusters
    async def reset_vector_index(self, collection_name: str, index_type: PGVectorIndexTypesEnum.HNSW.value):
        self.logger(f"Start: Resetting index for {collection_name}")

        index_name = self.table_index_name(collection_name)
        session: AsyncSession

        async with self.db_client() as session:
            async with session.begin():
                drop_index_stmt = sql_text(
                    f'DROP INDEX IF EXISTS {index_name}'
                )

                await session.execute(drop_index_stmt)
                await session.commit()

        # re-create
        return await self.create_vector_index(collection_name = collection_name, index_type = index_type)

