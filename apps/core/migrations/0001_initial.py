import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OutboxMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(db_index=True, max_length=100)),
                ('payload', models.JSONField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('sent', 'Sent'), ('failed', 'Failed')], db_index=True, default='pending', max_length=20)),
                ('retry_count', models.IntegerField(default=0)),
                ('max_retries', models.IntegerField(default=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookSubscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=2048)),
                ('event_types', models.JSONField(default=list)),
                ('secret', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookDelivery',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_id', models.UUIDField(db_index=True)),
                ('event_type', models.CharField(max_length=100)),
                ('payload', models.JSONField()),
                ('status_code', models.IntegerField(blank=True, null=True)),
                ('response_body', models.TextField(blank=True, null=True)),
                ('is_success', models.BooleanField(default=False)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('webhook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='core.webhooksubscription')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='outboxmessage',
            index=models.Index(fields=['status', 'created_at'], name='core_outbox_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(fields=['event_id', 'webhook'], name='core_webhook_event_id_idx'),
        ),
    ]
