import logging
import json
import os

class appender(dict):
    
    def __init__(self):
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
        
        if pd not in self.rets:
            self.rets.add(pd)
            self[pd] = {}
        
        self[pd][kd] = self.read_value(kv)
    
    def read_line(self, line):
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
            return self.write_depths[self.depth](k, v)
        
        logging.warning(f'unsupported depth: {self.depth}')
        depth_error
    
    def read_next_block(self):
        filename = self.filename
        if self.block > 0:
            filename += f'_{self.block:02d}'
        
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
            logging.debug(f'Reading {filename} ({size/1000000:,}mb)')
            self.do_time = True
        
        with open(filename, 'r', encoding=self.encoding) as fh:
            for x in fh.readlines()[1:]:
                self.read_line(x.strip())
            
            fh.close()
        
        return True
    
    def read(self,
             filename=None,
             encoding='utf8',
             parse=True,
             force=False):

        if force:
            self = {}
        
        if filename:
            self.filename = filename
        
        self.encoding = encoding
        self.parse = parse
        self.force = force
        
        self.do_time = False
        self.block = 0
        
        self.rets = set(self)
        
        try:
            while self.read_next_block():
                self.block += 1
        
        except Exception as e:
            logging.error("SERIUS DATA PARSE ERROR", exc_info=True)
            logging.error(f'While reading {filename}')
            logging.error(line)
    
    def write_block(self, line, out):
        self.block = line // self.volsize
        
        filename = self.filename
        if self.volsize and self.block:
            filename += f'_{self.block:02d}'
        
        self.prepare_file(filename)
        mod = os.stat(filename).st_mtime
        
        with open(filename, 'a', encoding=self.encoding) as fh:
            fh.write(out)
            fh.close()
        
        if mod == self.modified_date.get(filename):
            info = os.stat(filename)
            self.modified_date[filename] = info.st_mtime
    
    def write(self,
              newdata,
              depth=None,
              filename=None,
              encoding='utf8',
              volsize=25000):
        
        self.encoding = encoding
        self.volsize = volsize
        self.block = 0
        
        if filename:
            self.filename = filename
        
        if depth:
            self.depth = depth
        
        if self.filename and not self:
            self.read(force=True)
        
        line = len(self)
        out = ''
        for k, v in newdata.items():
            line += 1
            out += self.write_line(k, v)
            
            if line % volsize == 0 and out:
                self.write_block(line, out)
                out = ''
        
        if out:
            self.write_block(line, out)
    
    def write_all(self,
                  filename,
                  volsize=25000):
        
        self.volsize = volsize
        self.filename = filename
        
        line = 0
        lineold = 0
        out = ''
        for k, v in self.items():
            line += 1
            out += self.write_line(k, v)
            
            if line % volsize == 0 and out:
                self.write_block(lineold, out)
                out = ''
                lineold, line = int(line)
        
        if out:
            self.write_block(lineold, out)
