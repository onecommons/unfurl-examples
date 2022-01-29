This repository contains examples of Unfurl ensembles and service templates.

The default ensemble will create a compute instance of your cloud provider of choice (AWS and Google Cloud currently supported) and deploy the Docker image you specified.

* Expose the container's port over https (using Traefik).
* Provision Let's Encrypt certificates
* Register the deployed server with your DNS provider.

See the `inputs` section at the top of `ensemble-template.yaml` for the inputs you need to configure.

You can also use import the service templates found here into your own Unfurl projects. See https://github.com/onecommons/unfurl-campsite for an example project that uses the templates defined here.
