from unfurl.configurator import Configurator


class MetadataConfigurator(Configurator):
    def run(self, task):
        task.logger.info("Fetching machine types")
        task.target.attributes["machine_types"] = list(self.all_machine_types(task))
        yield task.done(True)

    def can_dry_run(self, task):
        return True

    @staticmethod
    def all_machine_types(task):
        # delay imports until now so the python package can be installed first
        import boto3
        from botocore.exceptions import BotoCoreError

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
