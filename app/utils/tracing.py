# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from typing import Any

import google.cloud.storage as storage
from google.api_core import exceptions as gcs_exceptions
from google.cloud import logging as google_cloud_logging
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult


class CloudTraceLoggingSpanExporter(CloudTraceSpanExporter):
    """
    An extended version of CloudTraceSpanExporter that logs span data to Google Cloud Logging
    and handles large attribute values by storing them in Google Cloud Storage.

    This class helps bypass the 256 character limit of Cloud Trace for attribute values
    by leveraging Cloud Logging (which has a 256KB limit) and Cloud Storage for larger payloads.
    """

    def __init__(
        self,
        logging_client: google_cloud_logging.Client | None = None,
        storage_client: storage.Client | None = None,
        bucket_name: str | None = None,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the exporter with Google Cloud clients and configuration.

        :param logging_client: Google Cloud Logging client
        :param storage_client: Google Cloud Storage client
        :param bucket_name: Name of the GCS bucket to store large payloads
        :param debug: Enable debug mode for additional logging
        :param kwargs: Additional arguments to pass to the parent class
        """
        super().__init__(**kwargs)
        self.debug = debug
        self.logging_client = logging_client or google_cloud_logging.Client(
            project=self.project_id
        )
        self.logger = self.logging_client.logger(__name__)
        self.storage_client = storage_client or storage.Client(project=self.project_id)
        self.bucket_name = (
            bucket_name or f"{self.project_id}-facilitador-logs-data"
        )
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self._gcs_disabled = os.getenv("TRACING_DISABLE_GCS", "false").lower() == "true"
        self._gcs_permission_denied = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export the spans to Google Cloud Logging and Cloud Trace.

        :param spans: A sequence of spans to export
        :return: The result of the export operation
        """
        for span in spans:
            span_context = span.get_span_context()
            trace_id = format(span_context.trace_id, "x")
            span_id = format(span_context.span_id, "x")
            span_dict = json.loads(span.to_json())

            span_dict["trace"] = f"projects/{self.project_id}/traces/{trace_id}"
            span_dict["span_id"] = span_id

            span_dict = self._process_large_attributes(
                span_dict=span_dict, span_id=span_id
            )

            if self.debug:
                print(span_dict)

            # Log the span data to Google Cloud Logging
            self.logger.log_struct(
                span_dict,
                labels={
                    "type": "agent_telemetry",
                    "service_name": "facilitador",
                },
                severity="INFO",
            )
        # Export spans to Google Cloud Trace using the parent class method
        return super().export(spans)

    def store_in_gcs(self, content: str, span_id: str) -> str:
        """
        Initiate storing large content in Google Cloud Storage/

        :param content: The content to store
        :param span_id: The ID of the span
        :return: The  GCS URI of the stored content
        """
        if self._gcs_disabled:
            return "GCS tracing disabled"

        try:
            if not self.storage_client.bucket(self.bucket_name).exists():
                logging.warning(
                    "Bucket %s not found. Unable to store span attributes in GCS.",
                    self.bucket_name,
                )
                return "GCS bucket not found"
        except gcs_exceptions.Forbidden as exc:
            if not self._gcs_permission_denied:
                logging.warning(
                    "No permission to check bucket %s for tracing spans: %s", self.bucket_name, exc
                )
            self._gcs_permission_denied = True
            self._gcs_disabled = True
            return "GCS permission denied"
        except gcs_exceptions.NotFound as exc:
            logging.warning("Tracing bucket %s not found: %s", self.bucket_name, exc)
            self._gcs_disabled = True
            return "GCS bucket not found"
        except gcs_exceptions.GoogleAPICallError as exc:  # pragma: no cover - defensive
            logging.warning("Failed to validate tracing bucket %s: %s", self.bucket_name, exc)
            return "GCS bucket validation failed"

        blob_name = f"spans/{span_id}.json"
        blob = self.bucket.blob(blob_name)

        try:
            blob.upload_from_string(content, "application/json")
        except gcs_exceptions.Forbidden as exc:
            if not self._gcs_permission_denied:
                logging.warning(
                    "No permission to upload span %s to bucket %s: %s", span_id, self.bucket_name, exc
                )
            self._gcs_permission_denied = True
            self._gcs_disabled = True
            return "GCS permission denied"
        except gcs_exceptions.NotFound as exc:
            logging.warning("Tracing bucket %s not found during upload: %s", self.bucket_name, exc)
            self._gcs_disabled = True
            return "GCS bucket not found"
        except gcs_exceptions.GoogleAPICallError as exc:  # pragma: no cover - defensive
            logging.warning(
                "Failed to upload span %s to bucket %s: %s", span_id, self.bucket_name, exc
            )
            return "GCS upload failed"

        return f"gs://{self.bucket_name}/{blob_name}"

    def _process_large_attributes(self, span_dict: dict, span_id: str) -> dict:
        """
        Process large attribute values by storing them in GCS if the entire
        span dictionary exceeds the size limit of Google Cloud Logging.

        :param span_dict: The span data dictionary
        :param span_id: The span ID
        :return: The updated span dictionary
        """
        # Google Cloud Logging has a 256KB limit per entry. We check against a slightly
        # smaller limit to leave a buffer.
        LOG_ENTRY_SIZE_LIMIT = 250 * 1024  # 250 KB

        try:
            serialized_span = json.dumps(span_dict).encode("utf-8")
            current_size = len(serialized_span)
        except TypeError:
            # If serialization fails, we can't determine the size, so we proceed cautiously.
            current_size = LOG_ENTRY_SIZE_LIMIT + 1

        if current_size > LOG_ENTRY_SIZE_LIMIT:
            original_attributes = span_dict.get("attributes")
            if not original_attributes:
                # Nothing to offload, but the span is still too large.
                # We can't do much here, but we'll log a warning.
                logging.warning(
                    "Span %s exceeds size limit but has no attributes to offload.",
                    span_id,
                )
                return span_dict

            logging.info(
                "Span %s with size %s KB exceeds limit, offloading attributes to GCS.",
                span_id,
                round(current_size / 1024),
            )

            # Store the complete original attributes payload in GCS
            gcs_uri = self.store_in_gcs(json.dumps(original_attributes), span_id)

            # Create a new, minimal set of attributes that replaces the large one
            new_attributes = {
                "payload_offloaded": "true",
                "original_attribute_count": len(original_attributes),
                "gcs_payload_uri": gcs_uri,
                "gcs_payload_url": (
                    f"https://storage.mtls.cloud.google.com/"
                    f"{self.bucket_name}/spans/{span_id}.json"
                ),
            }

            # Replace the original attributes with our new pointer attributes
            span_dict["attributes"] = new_attributes

        return span_dict
