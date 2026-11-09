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
from pathlib import Path
from hashlib import file_digest
from multiprocessing import Pool

HASH_ALGORITHM = 'sha256'

class Color:
	GREEN = '\033[92m'
	YELLOW = '\033[93m'
	RED = '\033[91m'
	END = '\033[0m'

class FileHash:
	def __init__(self, path: Path, s256hash: str):
		self.path = path
		self.s256hash = s256hash
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

	dir2 = Path(sys.argv[2])
	files2 = [f for f in dir2.rglob('*') if f.is_file()]

	with Pool() as pool:
		fileHashes1 = pool.map(hashFile, files1)
		fileHashes2 = pool.map(hashFile, files2)

	merged: list[str] = []
	for f in fileHashes1:
		f.setRelative(dir1)
		merged.append(f.relative)
	for f in fileHashes2:
		f.setRelative(dir2)
		if f.relative not in merged:
			merged.append(f.relative)
	sorted_merged = sorted(merged, key=str.casefold)

	for f in sorted_merged:
		entry1 = next((obj for obj in fileHashes1 if obj.relative == f), None)
		entry2 = next((obj for obj in fileHashes2 if obj.relative == f), None)

		color = ''
		modification = ''
		if entry1 == None and entry2 != None:
			color = Color.GREEN
			modification = 'Added'
		if entry1 != None and entry2 == None:
			color = Color.RED
			modification = 'Removed'
		if entry1 and entry2 and entry1.s256hash != entry2.s256hash:
			color = Color.YELLOW
			modification = 'Changed'
		if entry1 and entry2 and entry1.s256hash == entry2.s256hash:
			color = Color.END
			modification = 'Unchanged'

		print(f'{color}{f}: {entry1.s256hash if entry1 else 'Not present'} -> {entry2.s256hash if entry2 else 'Not present'}: {modification}{Color.END}')
