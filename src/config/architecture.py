from dataclasses import dataclass

@dataclass
class SystemConfig:
    max_concurrent_sends: int = 10000
    rate_limit_per_second: int = 500
    max_template_size: int = 5_000_000  # 5MB
    supported_email_providers = ['smtp', 'aws_ses', 'sendgrid', 'mailgun']
