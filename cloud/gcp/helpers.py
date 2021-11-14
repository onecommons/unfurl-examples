import logging
import os

from google.api_core.exceptions import GoogleAPIError
from google.cloud.compute_v1 import ListMachineTypesRequest, MachineTypesClient
from toscaparser.elements.scalarunit import ScalarUnit_Size
from unfurl.configurator import Configurator

log = logging.getLogger(__file__)


def choose_machine_type(ctx, args=None):
    """Choose machine type based on memory and cpu"""
    num_cpus, mem_size = attributes_from_host(ctx)
    types = args["machine_types"]
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


def attributes_from_host(ctx):
    host = None
    for capability in ctx.currentResource.capabilities:
        if capability.name == "host":
            host = capability
            break
    if not host:
        raise ValueError("Can't choose machine type - host info not provided")

    if "num_cpus" not in host.attributes or "mem_size" not in host.attributes:
        raise ValueError(
            "Can't choose machine type - num_cpus and mem_size must be provided"
        )

    num_cpus = host.attributes["num_cpus"]
    mem_size = host.attributes["mem_size"]
    mem_size = ScalarUnit_Size(mem_size).get_num_from_scalar_unit("MB")
    return num_cpus, mem_size


class MetadataConfigurator(Configurator):
    def run(self, task):
        task.logger.info("Fetching machine types")
        task.target.attributes["machine_types"] = list(self.all_machine_types())
        yield task.done(True)

    @staticmethod
    def all_machine_types():
        request = ListMachineTypesRequest()
        project = os.getenv("CLOUDSDK_CORE_PROJECT")
        zone = os.getenv("CLOUDSDK_COMPUTE_ZONE")
        if not project or not zone:
            raise ValueError(
                "Can't choose machine type - CLOUDSDK_COMPUTE_ZONE or CLOUDSDK_CORE_PROJECT not defined"
            )
        request.project = project
        request.zone = zone

        try:
            client = MachineTypesClient()
            response = client.list(request)
        except Exception as e:
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
