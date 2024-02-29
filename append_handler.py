import logging
import json
import os

class appender_base():
    
    def __init__(self, volsize=None):
        super().__init__(self)
        self.filename = None
        self.modified_date = {}
        self.read_depths = [
            self.read_line_key,
            self.read_line_single,
            self.read_line_split
            ]
        
        self.write_depths = [
            self.write_line_key,
            self.write_line_single,
            self.write_line_split
            ]
        
        self.depth = 1
        self.encoding = 'utf8'
        if volsize is None:
            volsize = 25000
        self.volsize = volsize
        self.lines = -1
        self.do_time = False
        self.keyonly = False
        self.dbg = []
        self.error_count = 0
    
    def setd(i):
        self = i
    
    @staticmethod
    def prepare_file(filename):
        if os.path.isfile(filename):
            return
        
        with open(filename, 'w') as fh:
            fh.write('# apdfile ' + filename)
            fh.close()
    
    def read_value(self, d):
        if self.parse:
            d = json.loads(d)
        
        return d
    
    def read_line_key(self, line):
        self[line] = 0
    
    def read_line_single(self, line):
        pd, kv = line.split('\t')
        self[pd] = self.read_value(kv)
    
    def read_line_split(self, line):
        pd, kd, kv = line.split('\t')
        
        if pd not in self:
            self[pd] = {}
        
        self[pd][kd] = self.read_value(kv)
    
    def read_line(self, line):
        if self.keyonly:
            self[line.split('\t')[0]] = 0
            return
        
        depth = line.count('\t')
        if 0 <= depth < len(self.read_depths):
            return self.read_depths[depth](line)
        
        logging.warning(f'unsupported depth: {depth}')
        depth_error
    
    def write_line_key(self, k, v):
        self[k] = 0
        return f'\n{k}'
    
    def write_line_single(self, k, v):
        self[k] = v
        return f'\n{k}\t{json.dumps(v)}'
    
    def write_line_split(self, k, v):
        self[k] = v
        out = ''
        for t, i in v.items():
            out += f'\n{k}\t{t}\t{json.dumps(i)}'
        
        return out
    
    def write_line(self, k, v):
        if 0 <= self.depth < len(self.write_depths):
            out = self.write_depths[self.depth](k, v)
            if self.keyonly:
                self[k] = 0
            
            return out
        
        logging.warning(f'unsupported depth: {self.depth}')
        depth_error
    
    def true_filename(self):
        if self.block > 0:
            return self.filename + f'_{self.block:02d}'
        
        return self.filename
    
    def read_next_block(self):
        filename = self.true_filename()
        
        if not os.path.isfile(filename):
            return
        
        info = os.stat(filename)
        
        if info.st_mtime != self.modified_date.get(filename):
            self.force = True
        
        if not self.force:
            return True
        
        self.modified_date[filename] = info.st_mtime
        
        size = info.st_size
        if self.do_time or size > 4000000:# >4mb
            dbg = self.dbg
            if self.keyonly and 'keyonly' not in dbg:
                dbg = dbg + ['keyonly']
            logging.debug(f'Reading {filename} ({size/1000000:,}mb) {" ".join(dbg)}')
            self.do_time = True
        
        with open(filename, 'r', encoding=self.encoding) as fh:
            for n, x in enumerate(fh.readlines()[1:]):
                try:
                    self.read_line(x.strip())
                except json.decoder.JSONDecodeError:
                    logging.warning(f'{self.filename} block {self.block}, line {n}, "{x}"')
                    self.error_count += 1
            
            fh.close()
        
        return True
    
    def read(self,
             filename=None,
             encoding='utf8',
             parse=True,
             force=False,
             dotime=None,
             keyonly=None):

        if force:
            self = {}
        
        if keyonly is not None:
            self.keyonly = keyonly
        
        if filename:
            self.filename = filename
        
        self.encoding = encoding
        self.parse = parse
        self.force = force
        
        if dotime != None:
            self.do_time = dotime
        
        self.block = 0
        
        #self.rets = set(self)
        
        try:
            while self.read_next_block():
                self.block += 1
        
        except Exception as e:
            logging.error("SERIUS DATA PARSE ERROR", exc_info=True)
            logging.error(f'While reading {filename} block {self.block}')
        
        if self.error_count:
            logging.error(f'Enncountered {self.error_count} parsing errors!')
        
        self.lines = len(self)
    
    def determine_block(self, line):
        if not self.volsize:
            return 0
        
        return line // self.volsize
    
    def write_block(self, line, out):
        self.block = self.determine_block(line)
        
        filename = self.filename
        if filename is None:
            return
        
        if self.block:
            filename += f'_{self.block:02d}'
        
        self.prepare_file(filename)
        mod = os.stat(filename).st_mtime
        
        with open(filename, 'a', encoding=self.encoding) as fh:
            fh.write(out)
            fh.close()
        
        if mod == self.modified_date.get(filename):
            info = os.stat(filename)
            self.modified_date[filename] = info.st_mtime
    
    def get_lines_fn(self, fn):
        if not os.path.isfile(fn):
            return 0
        
        i = 0
        with open(fn, encoding=self.encoding) as f:
            for i, _ in enumerate(f):
                pass
        
        return i
    
    def get_lines(self,
                  filename=None):# quick memory light
        if filename:
            self.filename = filename
        
        self.block = 0
        
        while os.path.isfile(self.true_filename()):
            self.block += 1
        
        self.block = max(0, self.block - 1)
        
        lines = self.get_lines_fn(self.true_filename())
        
        if self.block > 0:
            lines += self.get_lines_fn(self.filename) * self.block
        
        self.lines = lines
        return lines
    
    def write_helper(self, data, line):
        out = ''
        last_block = 0
        for k, v in data.items():
            this_block = self.determine_block(line)
            out += self.write_line(k, v)
            
            if this_block != last_block and out:
                self.write_block(line-1, out)
                out = ''
                last_block = this_block
            
            line += 1
            self.lines += 1
        
        if out:
            self.write_block(line, out)
    
    def write(self,
              newdata,
              depth=None,
              filename=None,
              encoding=None,
              volsize=None):

        if encoding is not None:
            self.encoding = encoding
        
        if volsize is not None:
            self.volsize = volsize
        
        self.block = 0
        
        if filename:
            self.filename = filename
        
        if depth is not None:
            self.depth = depth
        
        if self:
            line = len(self)
        
        elif self.lines > -1:
            line = self.lines
        
        elif self.filename and not self:
            line = self.get_lines()
        
        else:
            logging.error('FIlename not set when trying to write')
            line = 0
        
        self.write_helper(newdata, line)
    
    def write_all(self,
                  filename,
                  volsize=None):
        
        if volsize is not None:
            self.volsize = volsize
        
        self.filename = filename
        
        self.write_helper(self, 0)

class appender(appender_base, dict):
    pass

class appender_sharedkeys(appender):
    
    def __init__(self, volsize=None):
        super().__init__(volsize=volsize)
        self.skeys = []
        self.dbg.append('sharedkeys')
    
    def read_line_key(self, line):
        self[line] = []
    
    def add_keys(self, d):
        for k in d:
            if k not in self.skeys:
                self.skeys.append(k)
    
    def read_value_all(self, d):
        d = json.loads(d)
        if type(d) == dict:
            self.add_keys(d)
        
        l = [d.get(i, None) for i in self.skeys]
        return l
    
    def read_line_single(self, line):
        pd, kv = line.split('\t')
        self[pd] = self.read_value_all(kv)
    
    def read_line_split(self, line):
        pd, kd, kv = line.split('\t')
        
        #if pd not in self.rets:
        #    self.rets.add(pd)
        #    self[pd] = []

        self.add_keys([kd])

        pos = self.skeys.index(kd)
        while len(self[pd]) <= pos + 1:
            self[pd].append(None)
        
        self[pd][kd] = json.loads(kv)
    
    def write_line_key(self, k, v):
        self[k] = []
        return f'\n{k}'
    
    def write_line_single(self, k, v):
        self.add_keys(v)
        
        l = [v.get(i, None) for i in self.skeys]
        self[k] = l
        return f'\n{k}\t{json.dumps(v)}'
    
    def write_line_split(self, k, v):
        self.add_keys(v)
        
        l = [v.get(i, None) for i in self.skeys]
        self[k] = l
        
        out = ''
        for t, i in v.items():
            out += f'\n{k}\t{t}\t{json.dumps(i)}'
        
        return out
    
    def dget(self, k, d=None):
        k = self.get(k, d)
        if not k:
            return d
        
        d = {}
        for i, v in enumerate(k):
            if v != None:
                d[self.skeys[i]] = v
        
        return d


class appender_set(appender_base, set):
    
    def __init__(self, volsize=None):
        super().__init__(volsize=volsize)
        self.dbg.append('settype')
        #self = set()
    
    def read_value(self, d):
        if self.parse:
            d = json.loads(d)
        
        return d
    
    def read_line(self, line):
        if self.keyonly:
            self[line.split('\t')[0]] = 0
            return
        
        self.add(line)
    
    def write_line(self, k, v):
        self.add(k)
        return f'\n{k}'
    
    def write_helper(self, data, line):
        out = ''
        last_block = 0
        for k in data:
            this_block = self.determine_block(line)
            line += 1
            self.lines += 1
            out += self.write_line(k, 0)
            
            if this_block != last_block and out:
                self.write_block(line, out)
                out = ''
                last_block = this_block
        
        if out:
            self.write_block(line, out)