# WOPR File Header Templates

Use these at the top of every source file.

## Python Files (.py)

```python
#!/usr/bin/env python3
"""
WOPR - Wargaming Oversight & Position Recognition
Copyright (c) 2025 Bob Bomar <bob@bomar.us>
SPDX-License-Identifier: MIT

Brief description of what this file does.
"""
```

## Python Files (Alternate - More Detailed)

```python
#!/usr/bin/env python3
# WOPR - Wargaming Oversight & Position Recognition
# Copyright (c) 2025 Bob Bomar <bob@bomar.us>
# 
# This file is part of WOPR.
# Licensed under the MIT License - see LICENSE file for details.
#
# Description: Brief description of what this file does

"""Module docstring goes here."""
```

## YAML Files (.yaml, .yml)

```yaml
# WOPR - Wargaming Oversight & Position Recognition
# Copyright (c) 2025 Bob Bomar <bob@bomar.us>
# SPDX-License-Identifier: MIT
```

## Dockerfiles

```dockerfile
# WOPR - Wargaming Oversight & Position Recognition
# Copyright (c) 2025 Bob Bomar <bob@bomar.us>
# SPDX-License-Identifier: MIT

FROM python:3.11-slim
```

## Shell Scripts (.sh)

```bash
#!/bin/bash
# WOPR - Wargaming Oversight & Position Recognition
# Copyright (c) 2025 Bob Bomar <bob@bomar.us>
# SPDX-License-Identifier: MIT
#
# Description: Brief description of what this script does

set -e
```

## Markdown Files (.md)

```markdown
# File Title

Copyright (c) 2025 Bob Bomar <bob@bomar.us>  
Licensed under the MIT License - see [LICENSE](../LICENSE) file.

---
```

## JavaScript/React Files (.js, .jsx)

```javascript
/**
 * WOPR - Wargaming Oversight & Position Recognition
 * Copyright (c) 2025 Bob Bomar <bob@bomar.us>
 * SPDX-License-Identifier: MIT
 * 
 * Brief description of what this file does.
 */
```

## Configuration Files (if needed)

For files that don't support comments (JSON), add copyright to parent directory's README.

## Examples

### Camera Service

```python
#!/usr/bin/env python3
"""
WOPR - Wargaming Oversight & Position Recognition
Copyright (c) 2025 Bob Bomar <bob@bomar.us>
SPDX-License-Identifier: MIT

Camera service for WOPR. Runs on Raspberry Pi, captures images
via USB webcam and saves to NFS storage.
"""

from flask import Flask, jsonify, request
# ... rest of code
```

### Kubernetes Manifest

```yaml
# WOPR - Wargaming Oversight & Position Recognition
# Copyright (c) 2025 Bob Bomar <bob@bomar.us>
# SPDX-License-Identifier: MIT

apiVersion: apps/v1
kind: Deployment
metadata:
  name: wopr-cam_service
# ... rest of manifest
```

## Notes

- **SPDX-License-Identifier**: Standard way to identify license (tools can parse it)
- **Keep it brief**: Just copyright + license, details in LICENSE file
- **Consistency**: Use same format across all files in the project