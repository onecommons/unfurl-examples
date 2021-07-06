import json
import logging
import os

from google.api_core.exceptions import GoogleAPIError
from google.cloud.compute_v1 import ListMachineTypesRequest, MachineTypesClient
from toscaparser.elements.scalarunit import ScalarUnit_Size

log = logging.getLogger(__file__)


def choose_machine_type(ctx, args=None):
    """Choose machine type based on memory and cpu"""
    num_cpus, mem_size = attributes_from_host(args)
    types = json.loads(args["machine_types"])
    types = filter(lambda x: x["mem"] >= mem_size and x["cpu"] >= num_cpus, types)
    types = sorted(types, key=lambda x: (x["cpu"], x["mem"]))

    if types:
        log.info(
            "Selected machine type: %s [CPU: %s, Memory: %s MB]",
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


def attributes_from_host(args):
    if "num_cpus" not in args or "mem_size" not in args:
        raise ValueError(
            "Can't choose machine type - num_cpus and mem_size must be provided"
        )

    num_cpus = args["num_cpus"]
    mem_size = args["mem_size"]
    mem_size = ScalarUnit_Size(mem_size).get_num_from_scalar_unit("MB")
    return num_cpus, mem_size


def all_machine_types():
    request = ListMachineTypesRequest()
    project = os.getenv("GOOGLE_PROJECT")
    zone = os.getenv("GOOGLE_ZONE")
    if not project or not zone:
        raise ValueError(
            "Can't choose machine type - GOOGLE_ZONE or GOOGLE_PROJECT not defined"
        )
    request.project = project
    request.zone = zone

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


def list_all_machine_types(ctx):
    return json.dumps(list(all_machine_types()))
