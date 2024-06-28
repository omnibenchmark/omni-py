import io
import sys

import pytest
from packaging.version import Version

from omni.io.comparison import file_difference_between_benchmark_versions
from omni.io.MinIOStorage import MinIOStorage
from tests.io.MinIOStorage_setup import MinIOSetup, TmpMinIOStorage

if not sys.platform == "linux":
    pytest.skip(
        "for GHA, only works on linux (https://docs.github.com/en/actions/using-containerized-services/about-service-containers#about-service-containers)",
        allow_module_level=True,
    )

# setup and start minio container
minio_testcontainer = MinIOSetup(sys.platform == "linux")


class TestComparison:
    def test__file_difference_between_benchmark_versions_returns_correct(self):
        with TmpMinIOStorage(minio_testcontainer) as tmp:
            ss = MinIOStorage(auth_options=tmp.auth_options, benchmark=tmp.bucket_base)
            ss.set_current_version("0.1")
            result = ss.client.put_object(
                f"{ss.benchmark}.{ss.version.major}.{ss.version.minor}",
                f"testfile",
                io.BytesIO(b"abcd"),
                4,
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.{ss.version.major}.{ss.version.minor}",
                f"testfile2",
                io.BytesIO(b"abcdef"),
                6,
            )
            ss.set_new_version("0.2")
            ss.create_new_version()
            ss.set_current_version("0.2")
            result = ss.client.put_object(
                f"{ss.benchmark}.{ss.version.major}.{ss.version.minor}",
                f"testfile2",
                io.BytesIO(b"abcd"),
                4,
            )
            result = ss.client.put_object(
                f"{ss.benchmark}.{ss.version.major}.{ss.version.minor}",
                f"testfile3",
                io.BytesIO(b"abcd"),
                4,
            )
            out = file_difference_between_benchmark_versions(
                tmp.bucket_base,
                endpoint=tmp.auth_options["endpoint"],
                version1="0.1",
                version2="0.2",
            )
            outls = out.split("\n")
            outls2 = list()
            for line in outls:
                tl = line.split("\t")
                if len(tl) == 1:
                    outls2.append(line)
                elif len(tl) == 3:
                    outls2.append(tl[0] + tl[2])
            assert outls2 == [
                "*** version 0.1",
                "--- version 0.2",
                "***************",
                "*** 1,2 ****",
                "! testfile:e2fc714c4727ee9395f324cd2e7f331f",
                "! testfile2:e80b5017098950fc58aad83c8c14978e",
                "--- 1,3 ----",
                "! testfile:e2fc714c4727ee9395f324cd2e7f331f",
                "! testfile2:e2fc714c4727ee9395f324cd2e7f331f",
                "! testfile3:e2fc714c4727ee9395f324cd2e7f331f",
                "",
            ]


def cleanup_buckets_on_exit():
    """Cleanup a testing directory once we are finished."""
    TmpMinIOStorage(minio_testcontainer).cleanup_buckets()


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""
    request.addfinalizer(cleanup_buckets_on_exit)
