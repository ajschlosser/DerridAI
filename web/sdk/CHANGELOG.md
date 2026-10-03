<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# DerridAI SDK changelog

## 0.1.1

- Preserve cancellation as cancellation across Record loading, embedding, and generation instead of degrading aborted operations into provider fallback warnings.
- Validate explicitly declared embedding model and revision metadata before semantic retrieval, and validate returned embedding provenance when supplied.
- Deduplicate retrieval candidates deterministically by stable `record_id` before scoring and expose `duplicatesRemoved` in search diagnostics.
- Add an external-consumer packaging gate that installs the packed SDK into a separate TypeScript/Vite application and exercises Search and Research.

## 0.1.0

- Initial framework-neutral SDK release with inline/HTTP publication data sources, keyword/semantic/hybrid retrieval, MMR, evidence packets, citations, annotations, and injected embedding/generation capabilities.
