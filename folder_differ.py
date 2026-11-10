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
from difflib import SequenceMatcher

HASH_ALGORITHM = 'sha256'

class Color:
	GREEN = '\033[92m'
	BLUE = '\033[94m'
	YELLOW = '\033[93m'
	RED = '\033[91m'
	END = '\033[0m'

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
	if (len(sys.argv) < 4):
		print(f'Usage: {sys.argv[0]} <source_folder_1> <source_folder_2> <output_tsv>')
		quit()
	with open(sys.argv[3], 'w', encoding='utf-8') as fd:
		fd.write(f'Comparing {sys.argv[1]} to {sys.argv[2]}\n')
		fd.write(f'Original Filename\tOriginal Size (bytes)\tOriginal Hash\tUpdated Filename\tUpdated Size (bytes)\tUpdated Hash\tStatus\n')
		dir1 = Path(sys.argv[1])
		files1 = [f for f in dir1.rglob('*') if f.is_file()]

		dir2 = Path(sys.argv[2])
		files2 = [f for f in dir2.rglob('*') if f.is_file()]

		with Pool() as pool:
			fileHashes1 = pool.map(hashFile, files1)
			fileHashes2 = pool.map(hashFile, files2)

		rpaths1: list[str] = []
		rpaths2: list[str] = []
		rpaths_added_or_deleted: list[str] = []
		merged: list[str] = []
		for f in fileHashes1:
			f.setRelative(dir1)
			rpaths1.append(f.relative)
			merged.append(f.relative)
		for f in fileHashes2:
			f.setRelative(dir2)
			rpaths2.append(f.relative)
			if f.relative not in merged:
				merged.append(f.relative)
				rpaths_added_or_deleted.append(f.relative)
		for p in rpaths1:
			if p not in rpaths2:
				rpaths_added_or_deleted.append(p)
		
		sorted_merged = sorted(merged, key=str.casefold)

		renamed: list[str] = []
		for f in sorted_merged:
			if f in renamed: continue
			
			entry1 = next((obj for obj in fileHashes1 if obj.relative == f), None)
			entry2 = next((obj for obj in fileHashes2 if obj.relative == f), None)
			
			# Detect files that are identical, but have merely been renamed or moved
			if entry2 == None or entry1 == None:
				this_entry = entry2 if entry2 else entry1
				this_hlist = fileHashes2 if entry2 else fileHashes1
				other_hlist = fileHashes1 if entry2 else fileHashes2
				other_hlist_matches: list[str] = []
				for h in other_hlist:
					if (h.relative not in renamed) and (h.relative in rpaths_added_or_deleted) and (h.s256hash == this_entry.s256hash):
						other_hlist_matches.append(h.relative)
				if len(other_hlist_matches) > 0:
					# Check for any other matching hashes in this list, too
					this_hlist_matches: list[str] = []
					for h in this_hlist:
						if (h.relative not in renamed) and (h.relative in rpaths_added_or_deleted) and (h.s256hash == this_entry.s256hash):
							this_hlist_matches.append(h.relative)
					if len(this_hlist_matches) == 1 and len(other_hlist_matches) == 1:
						# 1:1 match, simple and easy
						if entry2:
							entry1 = next((obj for obj in fileHashes1 if obj.relative == other_hlist_matches[0]), None)
						else:
							entry2 = next((obj for obj in fileHashes2 if obj.relative == other_hlist_matches[0]), None)
						renamed.append(entry1.relative)
						renamed.append(entry2.relative)
					else:
						# Try to identify which file got renamed to which...
						
						# List order of scores matches this_hlist_matches
						scores = []
						# Used to minimize duplicate work
						scores_already_calcd = []
						this_hlist_taken: list[int] = []
						other_hlist_taken: list[int] = []
						templist: list[float] = []
						
						#print(f'DEBUG: this_hlist_matches={this_hlist_matches}')
						#print(f'DEBUG: other_hlist_matches={other_hlist_matches}')
						
						for p1 in this_hlist_matches:
							# List order of a matches other_hlist_matches
							a: list[float] = []
							b: list[bool] = []
							for p2 in other_hlist_matches:
								a.append(0.0) # placeholder
								b.append(False)
							scores.append(a)
							scores_already_calcd.append(b)
						for p2 in this_hlist_matches:
							templist.append(0.0)
						
						viable_partner_i = -1
						this_i = this_hlist_matches.index(this_entry.relative)
						a = len(this_hlist_matches)
						b = len(other_hlist_matches)
						while a > 0 and b > 0:
							# Find the match which this_entry is closest to...
							for i2, p2 in enumerate(other_hlist_matches):
								if scores_already_calcd[this_i][i2] == False:
									scores[this_i][i2] = SequenceMatcher(None, this_entry.relative, p2).ratio()
									scores_already_calcd[this_i][i2] = True
								elif i2 in other_hlist_taken:
									
									scores[this_i][i2] = 0.0
							next_highscore_i = scores[this_i].index(max(scores[this_i]))
							
							# and which isn't a closer match to another entry in this_hlist_matches.
							i2 = next_highscore_i
							p2 = other_hlist_matches[i2]
							for i, p in enumerate(this_hlist_matches):
								if scores_already_calcd[i][i2] == False:
									# TODO: Maybe skew to favor similar filename over similar subfolder?
									scores[i][i2] = SequenceMatcher(None, p, p2).ratio()
									scores_already_calcd[i][i2] = True
								elif i in this_hlist_taken:
									scores[i][i2] = 0.0
								templist[i] = scores[i][i2]
							highscore_partner_i = templist.index(max(templist))
							if (highscore_partner_i == this_i) or (templist[highscore_partner_i] == scores[this_i][next_highscore_i]):
								viable_partner_i = next_highscore_i
								break
							a = a - 1
							b = b - 1
						if viable_partner_i == -1 and len(this_hlist_matches) == len(other_hlist_matches):
							print(f'ERROR: Failed to match available partner for "{this_entry.relative}" even though it should be able to pair up?')
							raise Exception()
						
						if viable_partner_i != -1:
							# Found most viable partner
							if entry2:
								entry1 = next((obj for obj in fileHashes1 if obj.relative == other_hlist_matches[viable_partner_i]), None)
							else:
								entry2 = next((obj for obj in fileHashes2 if obj.relative == other_hlist_matches[viable_partner_i]), None)
							renamed.append(entry1.relative)
							renamed.append(entry2.relative)
						else:
							# Couldn't find a partner that wasn't already taken.
							if entry2:
								renamed.append(entry2.relative)
							else:
								renamed.append(entry1.relative)

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
				if entry1.relative != entry2.relative:
					color = Color.BLUE
					modification = 'Moved'
				else:
					color = Color.END
					modification = 'Unchanged'

			# Only log differences
			if not (entry1 and entry2 and entry1.s256hash == entry2.s256hash and entry1.relative == entry2.relative):
				fd.write(f'{entry1.relative if entry1 else ''}\t{entry1.size if entry1 else ''}\t{entry1.s256hash if entry1 else ''}\t{entry2.relative if entry2 else ''}\t{entry2.size if entry2 else ''}\t{entry2.s256hash if entry2 else ''}\t{modification}\n')
			print(f'{color}{f}: {entry1.s256hash if entry1 else 'Not present'} -> {entry2.s256hash if entry2 else 'Not present'}: {modification}{Color.END}')
