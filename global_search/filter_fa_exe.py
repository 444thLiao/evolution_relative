from Bio import SeqIO,Entrez
from os.path import *
from tqdm import tqdm
import os
import numpy as np
from subprocess import check_call
import sys
from Bio import Entrez
from bin.ncbi_convert import edl
import io
import pandas as pd
def run(cmd):
    check_call(cmd,shell=True,stdout=open('/dev/null'))
kofam_scan = '/home-user/thliao/software/kofamscan/exec_annotation'


gene_info = {'kegg': {'nxrA': 'K00370',
                      'nxrB': 'K00371',
                      'hao': 'K10535',
                      'amoA': 'K10944',
                      'amoB': 'K10945',
                      'amoC': 'K10946'},
             'TIGFAM': {'nxrA': '',
                        'nxrB': '',
                        'hao': 'TIGR01703',
                        'amoA': 'TIGR03080',
                        'amoB': 'TIGR03079',
                        'amoC': 'TIGR03078'}}

def filter_by_relative_pos(full_df):
    pid2nuccore_ids = dict(zip(full_df.index,full_df.loc[:,'nuccore ID']))
    nuccore_ids = [v for k,v in pid2nuccore_ids.items()]
    _nuccore_summary = []
    nuccore_summary,failed = edl.esummary(db='nuccore',
                                    ids=nuccore_ids,
                                    result_func=lambda x: Entrez.read(io.StringIO(x)))
    if failed:
        _nuccore_summary,failed = edl.esummary(db='nuccore',
                                ids=failed,
                                result_func=lambda x: Entrez.read(io.StringIO(x)),
                                batch_size=1)
    nid2length = {}
    for result in nuccore_summary+_nuccore_summary:
        nid2length[result['AccessionVersion']] = result['Length'].real
    nid2length = {k:v for k,v in nid2length.items() if k in pid2nuccore_ids.values()}
    
    tqdm.write('%s need to manual adjust....' % len(set(pid2nuccore_ids.values()).difference(set(nid2length))))
    near_end_protein = []
    for idx,row in full_df.iterrows():
        end = row['end']
        start = row['start']
        nuccore_ID = pid2nuccore_ids[idx]
        length = nid2length.get(nuccore_ID,'')
        if length:
            if abs(end - length) <= 100 or start <=100:
                tqdm.write('near end :' + idx)
                near_end_protein.append(idx)
        else:
            return_v = input(f'nuccore ID is {nuccore_ID}; does not get any info, maybe wgs, please check it manually. protein id is {idx}, end at {end}. Y/y for indicated it near the end. ')
            if return_v.lower() == 'y':
                near_end_protein.append(idx)
            else:
                pass
    return near_end_protein
        
def filter_archaea(full_df):
    remained_ids = full_df.index[full_df.loc[:,'superkingdom']=='Bacteria']
    return remained_ids




full_df = pd.read_csv('nr_retrieve_amoC/filtered_by_kegg.faa_aln.dir/iqtree.treefile/info_dir/pro2full_info.tab',sep='\t',index_col=0)
records = list(SeqIO.parse('nr_retrieve_amoC/filtered_by_kegg.faa',format='fasta'))
remained_ids = filter_archaea(full_df)
num_ori = len(records)
near_end_protein = filter_by_relative_pos(full_df)

remained_records = [_ for _ in records if _.id in remained_ids]
remained_records = [_ for _ in remained_records if _.id not in near_end_protein]
with open('nr_retrieve_amoC/with_genome_Bacteria_intact.faa','w') as f1:
    SeqIO.write(remained_records,f1,format='fasta-2line')
print('remained %s fa' % len(remained_records))
print('original %s fa' % num_ori)

if __name__ == "__main__":
    import sys
    params = sys.argv[1:]
    
    