import json
import pytest
import time
from pyspark.sql import SparkSession
from kedro_datasets.pandas import ParquetDataSet
from kedro.io.core import DataSetError
from kedro_datasets.spark.spark_dataset import SparkDataSet
from kedro_datasets.spark.spark_streaming_dataset import SparkStreamingDataSet
from pyspark.sql.types import IntegerType, StringType, StructField, StructType



def sample_schema(schema_path):
    with open(schema_path, encoding='utf-8') as f:
        try:
            return StructType.fromJson(json.loads(f.read()))
        except Exception as exc:
            raise DataSetError(
                f"Contents of 'schema.filepath' ({schema_path}) are invalid. "
                f"Schema is required for streaming data load, Please provide a valid schema_path."
            ) from exc

@pytest.fixture
def sample_spark_streaming_df(tmp_path):
    schema = StructType(
        [
            StructField("sku", StringType(), True),
            StructField("new_stock", IntegerType(), True),
        ]
    )
    data = [("0001", 2), ("0001", 7), ("0002", 4)]
    schema_path = (tmp_path / "test.json").as_posix()
    with open(schema_path, "w") as f:
        json.dump(schema.jsonValue(), f)
    return SparkSession.builder.getOrCreate().createDataFrame(data, schema)


class TestStreamingDataSet:
    def test_load(self, tmp_path, sample_spark_streaming_df):
        filepath = (tmp_path / "test_streams").as_posix()
        schema_path = (tmp_path / "test.json").as_posix()

        spark_json_ds = SparkDataSet(
            filepath=filepath, file_format="json", save_args=[{"mode","overwrite"}]
        )
        spark_json_ds.save(sample_spark_streaming_df)

        streaming_ds = SparkStreamingDataSet(filepath=filepath, file_format="json",
                                          load_args={"schema": {"filepath": schema_path}}).load()
        assert streaming_ds.isStreaming
        schema = sample_schema(schema_path)
        assert streaming_ds.schema == schema

    def test_save(self, tmp_path, sample_spark_streaming_df):
        filepath = (tmp_path / "test_streams_input").as_posix()
        schema_path = (tmp_path / "test.json").as_posix()
        checkpoint_path = (tmp_path / "checkpoint").as_posix()

        spark_json_ds = SparkDataSet(
            filepath=filepath, file_format="json", save_args=[{"mode","overwrite"}]
        )
        spark_json_ds.save(sample_spark_streaming_df)

        streaming_ds = SparkStreamingDataSet(
            filepath=filepath, file_format="json",save_args={"checkpoint": checkpoint_path, "output_mode":"append"}
        )
        assert streaming_ds._exists(schema_path)


