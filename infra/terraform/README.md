# AWS production infrastructure

Terraform for the production environment should provision private networking, an internet-facing TLS load balancer, compute for API/worker services, encrypted PostgreSQL, encrypted Redis, IAM roles, CloudWatch logging and Secrets Manager integration.

This repository intentionally keeps the provider credentials and account-specific identifiers outside git. Use a remote Terraform state backend with encryption and locking before applying infrastructure.

## Deployment contract

- API listens on container port 8000.
- `/ready` is the load-balancer readiness endpoint.
- API and workers receive secrets from AWS Secrets Manager.
- PostgreSQL and Redis are private and have no public ingress.
- TLS is terminated at the load balancer.
- Twilio and Plivo voice callbacks use the public HTTPS endpoint and media streams use WSS.
- Scale API and worker replicas independently.

Before `terraform apply`, replace environment/account-specific values through a tfvars file kept outside git and configure the remote backend.
