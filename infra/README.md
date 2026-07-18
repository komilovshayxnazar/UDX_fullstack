# infra/

Reference IaC artifacts consumed by `.github/workflows/*.yml`. Nothing
here is applied automatically — you provision the AWS resources once
(see `AWS_DEPLOY.md`) and the workflows only push new images / bundles
and roll ECS/CloudFront.

## Files

| File                                    | Purpose                                          |
| --------------------------------------- | ------------------------------------------------ |
| `ecs-task-definition.template.json`     | Fargate task def with Secrets Manager wiring. The backend workflow substitutes `<ACCOUNT_ID>`, `<REGION>`, `<TASK_EXECUTION_ROLE_ARN>`, `<TASK_ROLE_ARN>`, `<IMAGE_URI>`, `<ALLOWED_ORIGINS>` at deploy time. |
| `s3-cloudfront-bucket-policy.json`      | Bucket policy granting only the CloudFront OAC access. Attach once after creating the bucket + distribution. |

## Not included here (do yourself, once)

- VPC + subnets + security groups
- ALB + listener + target group
- Route 53 records
- ACM certificates
- DocumentDB / ElastiCache / RDS clusters
- Neo4j EC2 instance or Aura workspace
- IAM roles for the GitHub Actions OIDC provider

Codifying those in Terraform / CDK is worth doing later, but the app
itself doesn't block on that — it only needs to know the resulting
endpoints (via Secrets Manager) at runtime.
