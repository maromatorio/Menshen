# This file is part of Spyrk.
#
# Spyrk is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Spyrk is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Spyrk.  If not, see <http://www.gnu.org/licenses/>.

"""Spyrk: Python module for Spark devices.

* SparkCloud class provides access to the Spark Cloud.
  >>> from spyrk import SparkCloud

Spyrk is licensed under LGPLv3.

http://github.com/Alidron/spyrk
"""

from .spark_cloud import SparkCloud
from .__about__ import (
    __title__, __summary__, __uri__, __version__,
    __author__, __email__, __license__, __copyright__,
)

__all__ = [
    'SparkCloud',
    
    '__title__', '__summary__', '__uri__', '__version__',
    '__author__', '__email__', '__license__', '__copyright__',
]
