import pandas as pd
from os.path import join,exists,basename,dirname,isdir
from glob import glob
import os
from subprocess import check_call

genome_info = './genome_info_full.xlsx'
g_df = pd.read_excel(genome_info, index_col=0)
g_df = g_df.loc[g_df.loc[:,'used']!='no',:]
all_g_ids = list(g_df.index)

indir = './genbank'
odir = './genome_protein_files'


indir = './refseq'
odir = './genome_protein_files2'
tmp_dir = './tmp'
prokka_p = "/usr/local/bin/prokka"

def run_cmd(cmd):
    check_call(cmd,shell=True)

def get_faa_from_prokka_r(infile,odir,sample_name):
    locustag = f'{sample_name}'.split('_')[-1].split('.')[0]
    if exists(f'{odir}/{sample_name}'):
        return f'{odir}/{sample_name}/{sample_name}.faa'
    run_cmd(f'{prokka_p} {infile} --outdir {odir}/{sample_name} --force --prefix {sample_name} --locustag {locustag} --cpus 0 ')
    return f'{odir}/{sample_name}/{sample_name}.faa'

if not exists(odir):
    os.makedirs(odir,exist_ok=True)
if not exists(tmp_dir):
    os.makedirs(tmp_dir,exist_ok=True)
for p_dir in glob(join(indir,'**','GCA*'),recursive=True):
    if isdir(p_dir) and basename(p_dir) in all_g_ids:
        p_files = glob(join(p_dir,'*.faa.gz'))
        if not p_files:
            fna_file = glob(join(p_dir,'*.fna.gz'))[0]
            new_fna = fna_file.replace('.gz','')
            check_call(f'gunzip -d -c {fna_file} > {new_fna}',shell=True)
            p_files = [get_faa_from_prokka_r(new_fna,tmp_dir,basename(dirname(fna_file)))]
        p_file = p_files[0]
        ofile = join(odir,basename(p_dir)) +'.faa'
        if (not exists(ofile)) and p_file.endswith('.gz') and exists(p_file):
            check_call(f'gunzip -d -c {p_file} >{ofile}',shell=True)
        elif (not exists(ofile)) and exists(p_file):
            check_call(f'cat {p_file} >{ofile}',shell=True)
        else:
            #print(p_file,ofile)
            pass

odir = './genome_protein_files'
for p_dir in glob(join(indir,'**','GCA*'),recursive=True):
    if isdir(p_dir) and basename(p_dir) in all_g_ids:
        p_files = glob(join(p_dir,'*.faa.gz'))
        if not p_files:
            fna_file = glob(join(p_dir,'*.fna.gz'))[0]
            new_fna = fna_file.replace('.gz','')
            print(new_fna)
            continue
            #check_call(f'gunzip -d -c {fna_file} > {new_fna}',shell=True)
            #p_files = [get_faa_from_prokka_r(new_fna,tmp_dir,basename(dirname(fna_file)))]
            
        p_file = p_files[0]
        p_file = p_file.replace('protein.faa.gz','genomic.gff.gz')
        
        ofile = join(odir,'prokka_o',basename(p_dir),basename(p_dir)+ '.gff')
        os.makedirs(dirname(ofile),exist_ok=1)
        if (not exists(ofile)) and p_file.endswith('.gz') and exists(p_file):
            check_call(f'gunzip -d -c {p_file} >{ofile}',shell=True)
        elif (not exists(ofile)) and exists(p_file):
            check_call(f'cat {p_file} >{ofile}',shell=True)
        else:
            print(p_file,ofile)
            pass