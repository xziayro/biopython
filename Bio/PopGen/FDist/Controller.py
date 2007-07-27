# Copyright 2007 by Tiago Antao <tiagoantao@gmail.com>.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.



"""
This module allows to control fdist.

http://www.rubic.rdg.ac.uk/~mab/software.html
"""

import os
import tempfile
from sys import platform, maxint
from shutil import copyfile
from random import randint, random
from time import strftime, clock
#from logging import debug

class FDistController:
    def __init__(self, fdist_dir = ''):
        """Initializes the controller.
        
        fdist_dir is the directory where fdist2 is.
        
        The initializer checks for existance and executability of binaries.
        """
        self.tmp_idx = 0
        self.fdist_dir = fdist_dir
        self.os_name = os.name
        if self.os_name=='nt':
            ext = '.exe'
        else:
            ext = ''
        executable_list = ['datacal' + ext, 'fdist2' + ext,
            'cplot' + ext, 'pv' + ext]
        self.ext = ext
        exec_counts = 0
        #dir_contents = os.listdir(self.fdist_dir)
        #for file_name in executable_list:
        #    if file_name in dir_contents:
        #        if not os.access(self.fdist_dir +os.sep+ file_name, os.X_OK):
        #            raise IOError, file_name + " not executable"
        #    else:
        #        raise IOError, file_name + " not available"
        # #Doesn't work on jython, and doesn't make much sense...

    def _get_path(self, app):
        """Returns the path to an fdist application.
        """
        if self.fdist_dir == '':
            return app + self.ext
        else:
            return os.sep.join([self.fdist_dir, app]) + self.ext

    def _get_temp_file(self):
        """Gets a temporary file name.
        """
        if platform.startswith('java'): #no mkstemp, hack!
            self.tmp_idx += 1
            return strftime("%H%M%S") + str(int(clock()*100)) + str(randint(0,1000)) + str(self.tmp_idx)
        desc, name = tempfile.mkstemp()
        os.close(desc)
        return name

    def run_datacal(self, data_dir='.'):
        """Executes datacal.
        """
        in_name = data_dir + os.sep + self._get_temp_file()
        out_name = data_dir + os.sep + self._get_temp_file()
        f = open(in_name, 'w')
        f.write('a\n')
        f.close()
        curr_dir = os.getcwd()
        #os.chdir(data_dir)
        os.system('cd ' + data_dir+ ';' + self._get_path('datacal') + ' < ' + in_name + ' > ' + out_name)
        #os.chdir(curr_dir)
        f = open(out_name)
        fst_line = f.readline().rstrip().split(' ')
        fst = float(fst_line[4])
        sample_line = f.readline().rstrip().split(' ')
        sample = int(sample_line[9])
        f.close()
        os.remove(in_name)
        os.remove(out_name)
        return fst, sample
    
    def run_fdist(self, npops, nsamples, fst, sample_size,
        mut = 0, num_sims = 20000, data_dir='.'):
        """Executes fdist.
        
        Parameters
        npops - Number of populations
        nsamples - Number of populations sampled
        fst - expected Fst
        sample_size - Sample size per population
        mut - 1=Stepwise, 0=Infinite allele
        num_sims - number of simulations
        dir - directory where fdist will be executed (must be rw)
        
        Important Note: This can take quite a while to run!
        """
        if fst >= 0.9:
            #Lets not joke
            fst = 0.899
        if fst <= 0.0:
            #0  will make fdist run forever
            fst = 0.001
        in_name = 'input.fd'
        out_name = 'output.fd'
        #print 'writing', data_dir + os.sep + in_name
        f = open(data_dir + os.sep + in_name, 'w')
        f.write('y\n\n')
        f.close()
        f = open(data_dir + os.sep + 'fdist_params2.dat', 'w')
        f.write(str(npops) + '\n')
        f.write(str(nsamples) + '\n')
        f.write(str(fst) + '\n')
        f.write(str(sample_size) + '\n')
        f.write(str(mut) + '\n')
        f.write(str(num_sims) + '\n')
        f.close()
        inf = open(data_dir + os.sep + 'INTFILE', 'w')
        for i in range(98):
            inf.write(str(randint(-maxint+1,maxint-1)) + '\n') 
        inf.write('8\n')
        inf.close()

        os.system('cd ' + data_dir + '; ' +
            self._get_path('fdist2') + ' < ' + in_name + ' > ' + out_name)
        f = open(data_dir + os.sep + out_name)
        lines = f.readlines()
        f.close()
        for line in lines:
          if line.startswith('average Fst'):
            fst = float(line.rstrip().split(' ')[-1])
        os.remove(data_dir + os.sep + in_name)
        os.remove(data_dir + os.sep + out_name)
        return fst

    def run_fdist_force_fst(self, npops, nsamples, fst, sample_size,
        mut = 0, num_sims = 20000, data_dir='.', try_runs = 5000, limit=0.001):
        """Exectues fdist trying to force Fst.
        
        Parameters
        try_runs - number of simulations on the part trying to get
                   Fst correct.
        limit - interval limit
        """
        max_run_fst = 1
        min_run_fst = 0
        current_run_fst = fst
        old_fst = fst
        while True:
            #debug('testing fst ' +  str(current_run_fst))
            real_fst = self.run_fdist(npops, nsamples, current_run_fst, sample_size,
                mut, try_runs, data_dir)
            #debug('got real fst ' +  str(real_fst))
            if abs(real_fst - fst) < limit:
                #debug('We are OK')
                return self.run_fdist(npops, nsamples, current_run_fst, sample_size,
                    mut, num_sims, data_dir)
            old_fst = current_run_fst
            if real_fst > fst:
                max_run_fst = current_run_fst
                if current_run_fst < min_run_fst + limit:
                    #we can do no better
                    #debug('Lower limit is ' + str(min_run_fst))
                    return self.run_fdist(npops, nsamples, current_run_fst,
                        sample_size, mut, num_sims, data_dir)
                current_run_fst = (min_run_fst + current_run_fst)/2
            else:
                min_run_fst = current_run_fst
                if current_run_fst > max_run_fst - limit:
                    #we can do no better
                    #debug('Upper limit is ' + str(max_run_fst))
                    return self.run_fdist(npops, nsamples, current_run_fst,
                        sample_size, mut, num_sims, data_dir)
                current_run_fst = (max_run_fst + current_run_fst)/2

    def run_cplot(self, ci= 0.95, data_dir='.'):
        """Executes cplot.

        """
        in_name = self._get_temp_file()
        out_name = self._get_temp_file()
        f = open(data_dir + os.sep + in_name, 'w')
        f.write('out.dat out.cpl\n' + str(ci) + '\n')
        f.close()
        curr_dir = os.getcwd()
        os.system('cd ' + data_dir + ';'  +
            self._get_path('cplot') + ' < ' + in_name + ' > ' + out_name)
        os.remove(data_dir + os.sep + in_name)
        os.remove(data_dir + os.sep + out_name)
        f = open(data_dir + os.sep + 'out.cpl')
        conf_lines = []
        l = f.readline()
        try:
            while l<>'':
                conf_lines.append(
                    tuple(map(lambda x : float(x), l.rstrip().split(' ')))
                )
                l = f.readline()
        except ValueError:
            f.close()
            return []
        f.close()
        return conf_lines
        
    def run_pv(self, out_file='probs.dat', data_dir='.'):
        """Executes pv.

        """
        in_name = self._get_temp_file()
        out_name = self._get_temp_file()
        f = open(in_name, 'w')
        f.write('data_fst_outfile ' + out_file + ' out.dat\n')
        f.close()
        curr_dir = os.getcwd()
        os.chdir(data_dir)
        os.system(self._get_path('pv') + ' < ' + in_name + ' > ' + out_name)
        os.chdir(curr_dir)
        os.remove(in_name)
        os.remove(out_name)

