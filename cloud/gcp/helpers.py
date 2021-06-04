import logging

from google.api_core.exceptions import GoogleAPIError
from google.cloud.compute_v1 import ListMachineTypesRequest, MachineTypesClient
from unfurl.vendor.toscaparser.elements.scalarunit import ScalarUnit_Size

log = logging.getLogger(__file__)


def choose_machine_type(ctx):
    """Choose machine type based on memory and cpu"""
    num_cpus, mem_size = attributes_from_host(ctx)
    types = machine_types(num_cpus, mem_size)

    if types:
        return types[0]
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


def machine_types(num_cpus, mem_size):
    request = ListMachineTypesRequest()
    request.project = "unfurl-test"         # Change to your GCP Compute project
    request.zone = "us-central1-a"
    request.filter = "(guest_cpus={}) AND (memory_mb={})".format(num_cpus, mem_size)

    try:
        client = MachineTypesClient()
        response = client.list(request)
    except GoogleAPIError as e:
        log.error("GCP: %s", e)
        raise ValueError(
            "Can't find machine type ({} cpus, {} mem). Can't communicate with AWS.".format(
                num_cpus, mem_size
            )
        )

    return [item.name for item in response.items]
