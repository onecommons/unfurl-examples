import logging

import boto3
from botocore.exceptions import BotoCoreError
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
    host = ctx.currentResource.capabilities.get("host")
    if not host:
        raise ValueError("Can't choose machine type - host info not provided")
    if "num_cpus" not in host.properties or "mem_size" not in host.properties:
        raise ValueError(
            "Can't choose machine type - num_cpus and mem_size must be provided"
        )

    num_cpus = host.properties["num_cpus"]
    mem_size = host.properties["mem_size"]
    mem_size = ScalarUnit_Size(mem_size).get_num_from_scalar_unit("MiB")
    return num_cpus, mem_size


def all_machine_types():
    client = boto3.client("ec2")
    kwargs = {}
    try:
        while True:
            results = client.describe_instance_types(**kwargs)
            if "NextToken" not in results:
                break
            kwargs["NextToken"] = results["NextToken"]
            yield from (
                {
                    "name": it["InstanceType"],
                    "mem": it["MemoryInfo"]["SizeInMiB"],
                    "cpu": it["VCpuInfo"]["DefaultVCpus"],
                }
                for it in results["InstanceTypes"]
            )

    except BotoCoreError as e:
        log.error("AWS: %s", e)
        raise ValueError("Can't find machine types. Can't communicate with AWS.")
