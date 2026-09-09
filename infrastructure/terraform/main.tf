terraform { required_version=">= 1.8.0" required_providers { aws={source="hashicorp/aws",version="~> 6.0"} } }
provider "aws" { region=var.aws_region }
resource "aws_s3_bucket" "private" { bucket="ai-voice-${var.environment}-private-${data.aws_caller_identity.current.account_id}" }
resource "aws_s3_bucket_public_access_block" "private" { bucket=aws_s3_bucket.private.id;block_public_acls=true;block_public_policy=true;ignore_public_acls=true;restrict_public_buckets=true }
resource "aws_secretsmanager_secret" "app" { name="ai-voice/${var.environment}/app" }
data "aws_caller_identity" "current" {}
