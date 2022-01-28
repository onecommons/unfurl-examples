import os
from unfurl.configurator import Configurator


class MetadataConfigurator(Configurator):
    def run(self, task):
        task.logger.info("Fetching machine types")
        task.target.attributes["machine_types"] = list(self.all_machine_types(task))
        yield task.done(True)

    def can_dry_run(self, task):
        return True

    @staticmethod
    def all_machine_typesg(task):
        # delay imports until now so the python package can be installed first
        from google.cloud.compute_v1 import ListMachineTypesRequest, MachineTypesClient

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
            task.logger.error("GCP: %s", e)
            raise ValueError("Can't find machine types. Can't communicate with GCP.")

        yield from (
            {
                "name": item.name,
                "mem": item.memory_mb,
                "cpu": item.guest_cpus,
            }
            for item in response.items
        )
