import logging
import boto3
from botocore.exceptions import BotoCoreError
from toscaparser.elements.scalarunit import ScalarUnit_Size
from unfurl.configurator import Configurator

log = logging.getLogger(__file__)


def choose_machine_type(ctx, args):
    """Choose machine type based on memory and cpu"""
    num_cpus, mem_size = attributes_from_host(ctx)
    types = args["machine_types"]
    types = filter(lambda x: x["mem"] >= mem_size and x["cpu"] >= num_cpus, types)
    types = sorted(types, key=lambda x: (x["cpu"], x["mem"]))

    if types:
        log.info(
            "Selected machine type: %s [CPU: %s, Memory: %s MiB]",
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
    mem_size = ScalarUnit_Size(mem_size).get_num_from_scalar_unit("MiB")
    return num_cpus, mem_size


class MetadataConfigurator(Configurator):
    def run(self, task):
        task.logger.info("Fetching machine types")
        task.target.attributes["machine_types"] = list(self.all_machine_types(task))
        yield task.done(True)

    def can_dry_run(self, task):
        return True

    @staticmethod
    def all_machine_types(task):
        # for testing with moto, see if there's an endpoints_url set
        endpoint_url = task.query("$connections::AWSAccount::endpoints::ec2")
        client = boto3.client("ec2", endpoint_url=endpoint_url)
        try:
            paginator = client.get_paginator("describe_instance_types")
            for page in paginator.paginate():
                yield from (
                    {
                        "name": it["InstanceType"],
                        "mem": it["MemoryInfo"]["SizeInMiB"],
                        "cpu": it["VCpuInfo"]["DefaultVCpus"],
                    }
                    for it in page["InstanceTypes"]
                )
        except BotoCoreError as e:
            task.logger.error("AWS: %s", e)
            raise ValueError("Can't find machine types. Can't communicate with AWS.")
