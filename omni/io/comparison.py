import difflib

from omni.io.MinIOStorage import MinIOStorage


def file_difference_between_benchmark_versions(
    benchmark: str, endpoint: str, version1: str, version2: str
):
    mn = MinIOStorage({"endpoint": endpoint, "secure": False}, benchmark=benchmark)
    mn.set_current_version(version1)
    mn._get_objects()
    ls1 = [
        f"{i}:\t{mn.files[i]['last_modified']}\t{mn.files[i]['hash']}\n"
        for i in mn.files.keys()
    ]
    mn.set_current_version(version2)
    mn._get_objects()
    ls2 = [
        f"{i}:\t{mn.files[i]['last_modified']}\t{mn.files[i]['hash']}\n"
        for i in mn.files.keys()
    ]

    cli_output = "".join(
        list(
            difflib.context_diff(
                ls1, ls2, fromfile=f"version {version1}", tofile=f"version {version2}"
            )
        )
    )

    return cli_output
