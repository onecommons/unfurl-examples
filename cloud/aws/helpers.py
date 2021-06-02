import json
import logging
import os
import sys

from unfurl.vendor.toscaparser.elements.scalarunit import ScalarUnit_Size

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess


log = logging.getLogger(__file__)


def choose_machine_type(ctx):
    """Choose machine type based on memory and cpu"""
    host = ctx.currentResource.capabilities.get("host")
    if not host:
        raise ValueError("Can't choose machine type - host info not provided")
    if "num_cpus" not in host.properties or "mem_size" not in host.properties:
        raise ValueError("Can't choose machine type - num_cpus and mem_size must be provided")

    num_cpus = host.properties["num_cpus"]
    mem_size = host.properties["mem_size"]
    mem_size = ScalarUnit_Size(mem_size).get_num_from_scalar_unit("MB")
    aws_command = "aws ec2 describe-instance-types --query InstanceTypes[].InstanceType " \
                  "--filters Name=memory-info.size-in-mib,Values={} Name=vcpu-info.default-vcpus,Values={} " \
                  "--max-items 1".format(mem_size, num_cpus)
    try:
        process = subprocess.run(aws_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        log.error("AWS CLI: %s", e.stderr)
        raise ValueError(
            "Can't find machine type ({} cpus, {} mem). Can't communicate with AWS."
            .format(num_cpus, mem_size)
        )

    data = json.loads(process.stdout)
    if data:
        return data[0]
    raise ValueError("Can't find satisfactory machine type ({} cpus, {} mem).".format(num_cpus, mem_size))
