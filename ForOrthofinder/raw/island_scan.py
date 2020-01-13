
from glob import glob
import os
from collections import defaultdict
import pandas as pd
from os.path import *
from tqdm import tqdm
import pickle

Nif_list = ['K02591',
            'K02586',
            'K02588']
Nod_list = ['K14658',
            'K14659',
            'K14666',
            'K09695',
            'K09694',
            ]

Nif_list = ['K02584',
 'K02585',
 'K02586',
 'K02587',
 'K02588',
 'K02589',
 'K02590',
 'K02591',
 'K02592',
 'K02593',
 'K02594',
 'K02595',
 'K02596',
 'K02597',
 'K03737',
 'K03839',
 'K04488',
 'K15790']
Nod_list = [
 'K14657',
 'K14658',
 'K14659',
 'K14660',
 'K14661',
 'K14666',
 'K12546',
 'K18904',
 'K09694',
 'K09695',
 ]
# annotated_tab = "/home-user/jjtao/Rhizobiales/kegg_hmmsearch/e10/merged_result/merged_hmm_info.tab"
info_df = pd.read_csv("./nodnif_annotated_df.tsv",sep='\t',index_col=0)
# sub_df = info_df.loc[Nif_list+Nod_list,:]
# sub_df.to_csv('./nodnif_annotated_df.tsv',sep='\t',index=1)


OG_df = pd.read_csv('./subset_og.tsv',sep='\t',index_col=1)
tmp_dir = './.tmp'
if exists(join(tmp_dir,'genome2gene_info')):
    genome2gene_info = pickle.load(open(join(tmp_dir,'genome2gene_info'), 'rb'))
    genome2order_tuple = pickle.load(open(join(tmp_dir,'genome2order_tuple'), 'rb'))

# test nod
subset_df = info_df.loc[Nod_list,:]
Nod_genes = [_ for v in subset_df.values for g in v for _ in str(g).split(',') if not pd.isna(g)]


# test nif
subset_df = info_df.loc[Nif_list,:]
Nif_genes = [_ for v in subset_df.values for g in v for _ in str(g).split(',') if not pd.isna(g)]

except_names = []
for _ in OG_df.columns:
    if not exists(join('./tmp_gbk', f'{_}.gbk')):
        #print(_)
        except_names.append(_)

remap = {}
for _ in except_names:
    name = _.split('_')[-1]
    if len(glob(f'./tmp_gbk/*{name}.gbk'))!=1:
        print(_)
    else:
        remap[_] = glob(f'./tmp_gbk/*{name}.gbk')[0].split('/')[-1].replace('.gbk','')
         
remap['Bradyrhizobium_elkanii_TnphoA33'] = 'Bradyrhizobium_elkanii_TnphoA_33'
remap['Bradyrhizobium_sp_AS23_2'] = 'Bradyrhizobium_sp._AS23.2'
remap['Bradyrhizobium_sp_CNPSo_3424'] = 'Bradyrhizobium_sp._CNPSo_3424'
remap['Bradyrhizobium_sp_CNPSo_3426'] = 'Bradyrhizobium_sp._CNPSo_3426'
remap['Bradyrhizobium_sp_LMTR_3'] = 'Bradyrhizobium_sp._LMTR_3'
remap['Bradyrhizobium_sp_LVM_105'] = 'Bradyrhizobium_sp._LVM_105'
remap['Bradyrhizobium_sp_NAS80_1'] = 'Bradyrhizobium_sp._NAS80.1'
remap['Bradyrhizobium_sp_NAS96_2'] = 'Bradyrhizobium_sp._NAS96.2'
remap['Bradyrhizobium_sp_ORS_278_ORS278'] = 'Bradyrhizobium_sp._ORS_278'
remap['Bradyrhizobium_sp_ORS_285_ORS285'] = 'Bradyrhizobium_sp._ORS_285'
remap['Bradyrhizobium_sp_ORS_375_ORS375'] = 'Bradyrhizobium_sp._ORS_375'
remap['Bradyrhizobium_sp_cf659_CF659'] = 'Bradyrhizobium_sp._cf659'
remap['Pseudolabrys_sp_GY_H'] = 'Pseudolabrys_sp._GY_H'
remap['Rhodopseudomonas_thermotolerans_JA576_NBRC_108863_KCTC_15144'] = 'Rhodopseudomonas_thermotolerans_JA576'
remap['Oligotropha_carboxidovorans_OM5'] = 'Oligotropha_carboxidovorans_OM5_ATCC_49405'

genome2gene_info.pop('Oligotropha_carboxidovorans_OM5')

row = OG_df.iloc[0,:]
for col,v in row.items():
    v = v.split('|')[0]
    if v != col:
        remap[v] = col
        
OG_df.columns = [_ if _ not in remap else remap[_] for _ in OG_df.columns]

def count_number_contig(OG_df,genes,genome2gene_info,return_num=False):
    genome2num_contigs = defaultdict(set)
    for _ in genes:
        genome,gene = _.split('|')
        if genome not in genome2gene_info:
            genome = remap[genome]
        g2info = genome2gene_info[genome]
        contig = g2info[gene]['contig_name']
        genome2num_contigs[genome].add(contig)
    if return_num:
        genome2num_contigs = {k:len(v) for k,v in genome2num_contigs.items()}
    return genome2num_contigs


nod_genome2num_contigs = count_number_contig(OG_df,Nod_genes,genome2gene_info,return_num=True)
nif_genome2num_contigs = count_number_contig(OG_df,Nif_genes,genome2gene_info,return_num=True)

nod_genome2contigs = count_number_contig(OG_df,Nod_genes,genome2gene_info)
nif_genome2contigs = count_number_contig(OG_df,Nif_genes,genome2gene_info)

# nod and nif together
nod_nif_together_genomes = []
for genome,cset in nod_genome2contigs.items():
    cset2 = nif_genome2contigs.get(genome,set())
    if cset==cset2 and len(cset)==1:
        nod_nif_together_genomes.append(genome)
                
# extract_nifDKH
odir = './nif_neightbour100_genbank'
os.makedirs(odir,exist_ok=1)
neighbour = 50 * 1e3
for genome in [k for k,v in nif_genome2num_contigs.items() if v==1]:
    _nif_genes = [g for g in Nif_genes if remap.get(g.split('|')[0],g.split('|')[0]) == genome]
    f = f'./tmp_gbk/{genome}.gbk'
    if genome not in genome2gene_info:
        genome = remap[genome]
    g2info = genome2gene_info[genome]
    pos_list = []
    for gene in _nif_genes:
        gene = gene.split('|')[-1]
        pos1 = g2info[gene]['start']
        pos2 = g2info[gene]['end']
        contig = g2info[gene]['contig_name']
        pos_list+= [int(pos1),int(pos2)]
    if (max(pos_list) -min(pos_list)) >= 2*neighbour:
        continue
    
    start = int(min(pos_list) - neighbour )
    start = 0 if start <0 else start
    end = int(max(pos_list) + neighbour)
    if exists(f):
        genome_obj = [_ for _ in SeqIO.parse(f,format='genbank') if contig == _.id][0]
        new_genome = genome_obj[start:end]
        with open(join(odir,f'./{genome}.gbk'),'w') as f1:
            SeqIO.write([new_genome],f1,format='genbank')
    else:
        continue


# extract_fna
g2nod_region = defaultdict(list)
g2nif_region = defaultdict(list)
for genome in nod_nif_together_genomes:
    _nod_genes = [g for g in Nod_genes if remap.get(g.split('|')[0],g.split('|')[0]) == genome]
    _nif_genes = [g for g in Nif_genes if remap.get(g.split('|')[0],g.split('|')[0]) == genome]
    if genome not in genome2gene_info:
        genome = remap[genome]
    g2info = genome2gene_info[genome]
    for _genes,_region in zip([_nod_genes,
                               _nif_genes],
                              [g2nod_region,g2nif_region]):
        pos_list = []
        for gene in _genes:
            gene = gene.split('|')[-1]
            pos1 = g2info[gene]['start']
            pos2 = g2info[gene]['end']
            contig = g2info[gene]['contig_name']
            pos_list.append(pos1)
            pos_list.append(pos2)
            _region[genome].append(f'{contig}:{pos1}-{pos2}')
            

# too small to view
# gene distribution at the whole genome view
import plotly.graph_objs as go
from Bio import SeqIO
fig = go.Figure()
for g in g2nod_region:
    fig.add_scatter(x=[0,100],y=[g,g],mode='lines',line=dict(color='black',width=1),showlegend=False)
for _g2region in [g2nod_region,g2nif_region]:
    xs = []
    ys = []
    for genome,regions in tqdm(_g2region.items()):
        f = f'./tmp_gbk/{genome}.gbk'
        c = regions[0].split(':')[0]
        if exists(f):
            gb = [row for row in open(f).read().split('\n') if row.startswith('LOCUS') and c.split('.')[0] in row][0]
            idx = gb.split(' ').index('bp')
            num_length = int(gb.split(' ')[idx-1])
        else:
            continue
        for each_gene in regions:
            start,end = map(int,each_gene.split(':')[-1].split('-'))
            start,end = map(lambda x: x/num_length *100, [start,end])
            xs += [start,end,None]
            ys += [genome] *3
    fig.add_scatter(x=xs,y=ys,mode='lines+markers',line=dict(width=15))

fig.data[-2].marker.color = '#0000FF'
fig.data[-1].marker.color = '#FF0000'
fig.data[-2].name = 'Nod'
fig.data[-1].name = 'Nif'
fig.write_html('./test2.html')


# draw stack bar plot
def _tmp(x):
    x = x.split(':')[-1]
    s,e = map(int,x.split('-'))
    return abs(s-e)

fig = go.Figure()
for g in set(g2nod_region).union(set(g2nif_region)):
    regions1 = g2nod_region[g]
    regions2 = g2nif_region[g]
    _r = sorted(regions1+regions2,
                key=lambda x:int(x.split(':')[-1].split('-')[0]))
    total_length = sum([_tmp(_) for _ in _r])
    for gene in _r:
        length = _tmp(gene)
        if gene in regions1:
           fig.add_bar(x=[length/total_length *100],
                       y=[g],
                       orientation='h',
                       marker=dict(color='#0000FF')) 
        else:
           fig.add_bar(x=[length/total_length*100],
                       y=[g],
                       orientation='h',
                       marker=dict(color='#FF0000')) 
fig = fig.update_layout(barmode='stack')
fig.write_html('./test.html')