"""
Copyright (C) 2026 Joshua Herron

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses/>.
"""

import sys
import os
from pathlib import Path
from hashlib import file_digest
from multiprocessing import Pool

HASH_ALGORITHM = 'sha256'

class FileHash:
	def __init__(self, path: Path, s256hash: str):
		self.path = path
		self.s256hash = s256hash
		self.size = os.path.getsize(path)
		self.relative = ''

	def setRelative(self, dir: Path):
		self.relative = str(self.path.relative_to(dir)).replace('\\', '/')

def hashFile(f: Path) -> FileHash:
	with open(f, 'rb') as fd:
		digest = file_digest(fd, HASH_ALGORITHM).hexdigest()
		return FileHash(f, digest)

if __name__ == '__main__':
	if (len(sys.argv) < 3):
		print(f'Usage: {sys.argv[0]} <input_folder> <tsv_output_file>')
		quit()
	dir1 = Path(sys.argv[1])
	files1 = [f for f in dir1.rglob('*') if f.is_file()]

	with Pool() as pool:
		fileHashes1 = pool.map(hashFile, files1)

	for f in fileHashes1:
		f.setRelative(dir1)

	sortedFiles = sorted(fileHashes1, key=lambda key: key.relative.casefold())

	with open(sys.argv[2], 'w', encoding='utf-8') as fd:
		fd.write(f'Filename\tSize (bytes)\tHash\n')
		for f in sortedFiles:
			fd.write(f'{f.relative}\t{f.size}\t{f.s256hash}\n')
