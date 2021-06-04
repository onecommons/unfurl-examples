import logging

from google.api_core.exceptions import GoogleAPIError
from google.cloud.compute_v1 import ListMachineTypesRequest, MachineTypesClient
from toscaparser.elements.scalarunit import ScalarUnit_Size

log = logging.getLogger(__file__)


def choose_machine_type(ctx):
    """Choose machine type based on memory and cpu"""
    num_cpus, mem_size = attributes_from_host(ctx)
    types = all_machine_types()
    types = filter(lambda x: x["mem"] >= mem_size and x["cpu"] >= num_cpus, types)
    types = sorted(types, key=lambda x: (x["cpu"], x["mem"]))

    if types:
        log.info(
            "Selected machine type: %s [CPU: %s, Memory: %s]",
            types[0]["name"],
            types[0]["cpu"],
            types[0]["mem"],
        )
        return types[0]["name"]
    raise ValueError(
        "Can't find satisfactory machine type ({} cpus, {} mem).".format(
            num_cpus, mem_size
        )
    )


def attributes_from_host(ctx):
    host = ctx.currentResource.capabilities.get("host")
    if not host:
        raise ValueError("Can't choose machine type - host info not provided")
    if "num_cpus" not in host.properties or "mem_size" not in host.properties:
        raise ValueError(
            "Can't choose machine type - num_cpus and mem_size must be provided"
        )

    num_cpus = host.properties["num_cpus"]
    mem_size = host.properties["mem_size"]
    mem_size = ScalarUnit_Size(mem_size).get_num_from_scalar_unit("MB")
    return num_cpus, mem_size


def all_machine_types():
    request = ListMachineTypesRequest()
    request.project = "unfurl-test"         # Change to your GCP Compute project
    request.zone = "us-central1-a"

    try:
        client = MachineTypesClient()
        response = client.list(request)
    except GoogleAPIError as e:
        log.error("GCP: %s", e)
        raise ValueError("Can't find machine types. Can't communicate with GCP.")

    yield from (
        {
            "name": item.name,
            "mem": item.memory_mb,
            "cpu": item.guest_cpus,
        }
        for item in response.items
    )
