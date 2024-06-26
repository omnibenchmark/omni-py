import io
import sys

import pytest
from packaging.version import Version

from omni.io.MinIOStorage import MinIOStorage
from tests.io.MinIOStorage_setup import MinIOSetup, TmpMinIOStorage

if not sys.platform == "linux":
    pytest.skip(
        "for GHA, only works on linux (https://docs.github.com/en/actions/using-containerized-services/about-service-containers#about-service-containers)",
        allow_module_level=True,
    )

# setup and start minio container
minio_testcontainer = MinIOSetup(sys.platform == "linux")


class TestMinIOStorage:
    def test_init_fail(self):
        with pytest.raises(KeyError):
            ss = MinIOStorage(auth_options={}, benchmark="test")

    def test_init_success(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            assert ss.benchmark == tmp.bucket_base

    def test_init_public_success(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            _ = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss = MinIOStorage(
                auth_options=tmp.auth_options_readonly, benchmark=tmp.bucket_base
            )
            assert ss.benchmark == tmp.bucket_base

    def test__test_connect_success_with_valid_endpoint(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._test_connect()

    def test__get_containers_success_retrieve_buckets(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._get_containers()
            assert [ct in ss.containers for ct in [f"{tmp.bucket_base}.0.1"]] == [True]

    def test__get_benchmarks_success_retrieve_benchmarks(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._get_benchmarks()
            assert tmp.bucket_base in ss.benchmarks

        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._get_benchmarks(update=False)
            assert tmp.bucket_base in ss.benchmarks

    def test__create_benchmark_succes_create_benchmark(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._create_benchmark(f"{tmp.bucket_base}2")
            ss._get_benchmarks()

            assert f"{tmp.bucket_base}2" in ss.benchmarks

    def test__get_versions_sucess_get_version(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._get_versions()
            assert ss.versions == [Version("0.1")]

    def test__get_versions_sucess_get_other_version(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss._get_versions()
            assert ss.other_versions == ["test.1"]

    def test__get_versions_public_sucess_get_version(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            _ = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss = MinIOStorage(
                auth_options=tmp.auth_options_readonly, benchmark=tmp.bucket_base
            )
            ss._get_versions()
            assert ss.versions == [Version("0.1")]

    def test__get_versions_public_sucess_get_other_version(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            _ = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss = MinIOStorage(
                auth_options=tmp.auth_options_readonly, benchmark=tmp.bucket_base
            )
            ss._get_versions()
            assert ss.other_versions == ["test.1"]

    def test__update_overview_remove_inexisting(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            new_version = Version("0.2")
            result = ss.client.put_object(
                f"{ss.benchmark}.overview",
                f"{new_version.major}.{new_version.minor}",
                io.BytesIO(b""),
                0,
            )
            ss._update_overview()
            all_versions_in_overview = []
            for element in ss.client.list_objects(f"{ss.benchmark}.overview"):
                all_versions_in_overview.append(element.object_name)
            assert "0.2" not in all_versions_in_overview

    def test__create_new_version_fail_if_no_version_provided(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss.set_current_version()
            ss.set_new_version()
            ss._create_new_version()

    def test__create_new_version_success_if_version_provided(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss.set_new_version()
            ss._create_new_version()
            assert Version("0.2") in ss.versions

    def test__create_new_version_success_if_version_provided(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)

    def test__get_objects(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file1.txt", io.BytesIO(b""), 0
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file2.txt", io.BytesIO(b""), 0
            )
            ss.set_current_version()
            ss._get_objects()
            assert ss.files.keys() == {"file1.txt", "file2.txt"}
            assert ss.files["file1.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
            }
            assert ss.files["file2.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
            }
            assert ss.files["file1.txt"]["size"] == 0
            assert ss.files["file2.txt"]["size"] == 0
            assert ss.files["file1.txt"]["hash"] == "d41d8cd98f00b204e9800998ecf8427e"
            assert ss.files["file2.txt"]["hash"] == "d41d8cd98f00b204e9800998ecf8427e"
            assert len(ss.files["file1.txt"]["last_modified"]) > 0
            assert len(ss.files["file2.txt"]["last_modified"]) > 0

    def test__get_objects_public(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file1.txt", io.BytesIO(b""), 0
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file2.txt", io.BytesIO(b""), 0
            )
            ss = MinIOStorage(
                auth_options=tmp.auth_options_readonly, benchmark=tmp.bucket_base
            )
            ss.set_current_version()
            ss._get_objects()
            assert ss.files.keys() == {"file1.txt", "file2.txt"}
            assert ss.files["file1.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "x-object-meta-mtime",
                "accesstime",
            }
            assert ss.files["file2.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "x-object-meta-mtime",
                "accesstime",
            }
            assert ss.files["file1.txt"]["size"] == 0
            assert ss.files["file2.txt"]["size"] == 0
            assert ss.files["file1.txt"]["hash"] == "d41d8cd98f00b204e9800998ecf8427e"
            assert ss.files["file2.txt"]["hash"] == "d41d8cd98f00b204e9800998ecf8427e"
            assert len(ss.files["file1.txt"]["last_modified"]) > 0
            assert len(ss.files["file2.txt"]["last_modified"]) > 0

    def test_find_objects_to_copy(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file1.txt", io.BytesIO(b""), 0
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file2.txt", io.BytesIO(b""), 0
            )
            ss.set_current_version()
            ss.find_objects_to_copy(tagging_type="all")
            assert ss.files.keys() == {"file1.txt", "file2.txt"}
            assert ss.files["file1.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
            }
            assert ss.files["file2.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
            }
            assert type(ss.files["file1.txt"]["copy"]) == bool
            assert type(ss.files["file2.txt"]["copy"]) == bool

            with pytest.raises(ValueError):
                ss.find_objects_to_copy(tagging_type="other")

            with pytest.raises(ValueError):
                ss.find_objects_to_copy(reference_time="2024")

            import datetime

            ss.find_objects_to_copy(reference_time=datetime.datetime.now())
            assert ss.files.keys() == {"file1.txt", "file2.txt"}
            assert ss.files["file1.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
            }
            assert ss.files["file2.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
            }
            assert ss.files["file1.txt"]["copy"] == True
            assert ss.files["file2.txt"]["copy"] == True

    def test_copy_objects(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file1.txt", io.BytesIO(b""), 0
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file2.txt", io.BytesIO(b""), 0
            )
            ss.set_current_version()
            ss.set_new_version()
            ss.find_objects_to_copy()
            ss._create_new_version()
            ss.copy_objects()
            assert ss.files.keys() == {"file1.txt", "file2.txt"}
            assert ss.files["file1.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
                "copied",
            }
            assert ss.files["file2.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
                "copied",
            }
            assert type(ss.files["file1.txt"]["copied"]) == bool
            assert type(ss.files["file2.txt"]["copied"]) == bool

            with pytest.raises(NotImplementedError):
                ss.copy_objects(type="symlink")
            with pytest.raises(ValueError):
                ss.copy_objects(type="other")

    def test_create_new_version(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file1.txt", io.BytesIO(b""), 0
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.0.1", "file2.txt", io.BytesIO(b""), 0
            )
            ss.create_new_version("0.2")
            assert ss.files.keys() == {"file1.txt", "file2.txt"}
            assert ss.files["file1.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
                "copied",
            }
            assert ss.files["file2.txt"].keys() == {
                "hash",
                "last_modified",
                "size",
                "symlink_path",
                "copy",
                "copied",
            }
            assert type(ss.files["file1.txt"]["copied"]) == bool
            assert type(ss.files["file2.txt"]["copied"]) == bool


def cleanup_buckets_on_exit():
    """Cleanup a testing directory once we are finished."""
    TmpMinIOStorage(minio_testcontainer).cleanup_buckets()


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""
    request.addfinalizer(cleanup_buckets_on_exit)
