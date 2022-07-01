#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from xml.dom.minidom import ReadOnlySequentialNamedNodeMap
from xxlimited import new
from rdkit import Chem
from rdkit.Chem import AllChem, rdmolops, DataStructs, Lipinski, Descriptors
from openbabel import openbabel as ob

from crem.crem import grow_mol

from copy import deepcopy
from inspect import getfullargspec
import multiprocessing as mp
import tempfile, subprocess, os, random, time, shutil, tqdm
import numpy as np
import pandas as pd

import bz2
import pickle
import _pickle as cPickle


#==================================================
# Class to work with lead
#==================================================

# Remove fragments in the future
class Individual:

    def __init__(self,smiles:str = None, mol:Chem.rdchem.Mol = None, idx:int = 0, pdbqt = None, cost:float = np.inf) -> None:
        self.smiles = smiles
        
        if not mol:
            try:
                self.mol = Chem.MolFromSmiles(smiles)
            except:
                self.mol = None
        else:
            self.mol = mol
        
        self.idx = idx
        
        if not pdbqt:
            try:
                self.pdbqt = confgen(smiles, outformat = 'pdbqt')
            except:
                self.pdbqt = None
        else:
            self.pdbqt = pdbqt

        self.cost = cost
        
    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

class Local:
    def __init__(self, mol:Chem.rdchem.Mol, crem_db_path:str, costfunc:object, grow_crem_kwargs:dict = {}, costfunc_kwargs:dict = {}) -> None:
        self.mol = mol
        self.crem_db_path = crem_db_path
        self.grow_crem_kwargs = grow_crem_kwargs
        self.grow_crem_kwargs.update({'return_mol':True})
        self.costfunc = costfunc
        self.costfunc_kwargs = costfunc_kwargs

        self.pop = [Individual(Chem.MolToSmiles(self.mol), self.mol, idx = 0)]
    def __call__(self, njobs:int = 1, pick:int = None):
        new_mols = list(grow_mol(
            self.mol,
            self.crem_db_path,
            **self.grow_crem_kwargs
            ))
        if pick:
            random.shuffle(new_mols)
            new_mols = new_mols[:pick]
            new_mols = [Chem.RemoveHs(item[1]) for item in new_mols]

        idx0 = len(self.pop)
        for i, mol in enumerate(new_mols):
            self.pop.append(Individual(Chem.MolToSmiles(mol), mol, idx = idx0 + i))
        
        # Calculating cost of each individual
        # Creating the arguments
        args_list = []
        # Make a copy of the self.costfunc_kwargs
        kwargs_copy = self.costfunc_kwargs.copy()
        if 'wd' in getfullargspec(self.costfunc).args:
            costfunc_jobs = tempfile.TemporaryDirectory(prefix='costfunc')
            kwargs_copy['wd'] = costfunc_jobs.name
        
        for individual in self.pop:
            args_list.append((individual, kwargs_copy))

        print(f'Calculating cost function...')
        pool = mp.Pool(njobs)
        self.pop = [individual for individual in tqdm.tqdm(pool.imap(self.__costfunc__, args_list), total=len(args_list))]
        pool.close()
        
        if 'wd' in getfullargspec(self.costfunc).args: shutil.rmtree(costfunc_jobs.name)


    def __costfunc__(self, args_list):
        Individual, kwargs = args_list
        #This is just to use the progress bar on pool.imap
        return self.costfunc(Individual, **kwargs)
            
    def pickle(self,title, compress = False):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        if compress:
            compressed_pickle(title, result)
        else:
            full_pickle(title, result)
    
    def to_dataframe(self):
        list_of_dictionaries = []
        for Individual in self.pop:
            dictionary = Individual.__dict__.copy()
            del dictionary['mol']
            list_of_dictionaries.append(dictionary)
        return pd.DataFrame(list_of_dictionaries)       
        
#==================================================
# Define some functions to work with
#==================================================
# Useful as decorator
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % \
                  (method.__name__, (te - ts) * 1000))
        return result
    return timed

def run(command, shell = True, executable = '/bin/bash', Popen = False):
    if Popen:
        #In this case you could acces the pid as: run.pid
        process = subprocess.Popen(command, shell = shell, executable = executable, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text = True)
    else:
        process = subprocess.run(command, shell = shell, executable = executable, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text = True)
        returncode = process.returncode
        if returncode != 0:
            print(f'Command {command} returned non-zero exit status {returncode}')
            raise RuntimeError(process.stderr)
    return process

def obconvert(inpath, outpath):
    """Convert  molecule using openbabel

    Args:
        input (str, path): input molecule.
        output (str, path): must have the extension of the molecule.
    """
    in_ext = os.path.basename(inpath).split('.')[-1]
    out_ext = os.path.basename(outpath).split('.')[-1]

    obConversion = ob.OBConversion()
    obConversion.SetInAndOutFormats(in_ext, out_ext)
    mol = ob.OBMol()
    obConversion.ReadFile(mol, inpath)   # Open Babel will uncompressed automatically
    #mol.AddHydrogens()
    obConversion.WriteFile(mol, outpath)

def confgen(smiles, outformat = "pdbqt"):
    """Create a 3D model from smile to

    Args:
        smiles (str): a valid smiles code.
        outformat (str, optional): The output molecule extension. Defaults to "pdbqt".
    """
    molin = tempfile.NamedTemporaryFile(suffix='.mol')
    molout = tempfile.NamedTemporaryFile(suffix=f'.{outformat}')
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    AllChem.EmbedMolecule(mol)
    AllChem.MMFFOptimizeMolecule(mol)
    Chem.MolToMolFile(mol, molin.name)
    obconvert(molin.name, molout.name)
    with open(molout.name, 'r') as o:
        string = o.read()
    return string

def fragments(mol):
    break_point = int(random.choice(np.where(np.array([b.GetBondType() for b in mol.GetBonds()]) == Chem.rdchem.BondType.SINGLE)[0]))
    # Chem.FragmentOnBonds(mol, break_point) # Could be used to increase randomness give more possible fragments and select two of them
    with Chem.RWMol(mol) as rwmol:
        b = rwmol.GetBondWithIdx(break_point)
        rwmol.RemoveBond(b.GetBeginAtomIdx(), b.GetEndAtomIdx())
    return rdmolops.GetMolFrags(rwmol, asMols = True)

def rdkit_numpy_convert(fp):
    # fp - list of binary fingerprints
    output = []
    for f in fp:
        arr = np.zeros((1,))
        DataStructs.ConvertToNumpyArray(f, arr)
        output.append(arr)
    return np.asarray(output)

def get_top(ms, model):
    # ms - list of molecules
    # model - sklearn model
    fps1 = [AllChem.GetMorganFingerprintAsBitVect(m, 2) for m in ms]
    x1 = rdkit_numpy_convert(fps1)
    pred = model.predict(x1)
    i = np.argmax(pred)
    return ms[i], pred[i]

def get_sim(ms, ref_fps):
    # ms - list of molecules
    # ref_fps - list of fingerprints of reference molecules
    output = []
    fps1 = [AllChem.GetMorganFingerprintAsBitVect(m, 2) for m in ms]
    for fp in fps1:
        v = DataStructs.BulkTanimotoSimilarity(fp, ref_fps)
        i = np.argmax(v)
        output.append([v[i], i])
    return output

def get_similar_mols(mols:list, ref_mol:Chem.rdchem.Mol, pick:int, beta:float = 0.01):
    """Pick the similar molecules from mols respect to ref_mol using a roulette wheel selection strategy.

    Args:
        mols (list): the list of molecules from where pick molecules will be chosen
        ref_mol (Chem.rdchem.Mol): The reference molecule
        pick (int): Number of molecules to pick from mols
        beta (float, optional): Selection threshold. Defaults to 0.01.

    Returns:
        list: A list of picked molecules.
    """
    if pick >= len(mols):
        return mols
    else:
        ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2)
        fps = [AllChem.GetMorganFingerprintAsBitVect(mol, 2) for mol in mols]
        similarities = np.array(DataStructs.BulkTanimotoSimilarity(ref_fp, fps))
        probs = np.exp(beta*similarities) / np.sum(np.exp(beta*similarities))
        cumsum = np.cumsum(probs)
        indexes = set()
        while len(indexes) != pick:
            r = sum(probs)*np.random.rand()
            indexes.add(np.argwhere(r <= cumsum)[0][0])
        return [mols[index] for index in indexes]

def lipinski_filter(mol, maxviolation = 2):
    filter = {
        'NumHAcceptors': {'method':Lipinski.NumHAcceptors,'cutoff':10},
        'NumHDonors': {'method':Lipinski.NumHDonors,'cutoff':5},
        'wt': {'method':Descriptors.MolWt,'cutoff':500},
        'MLogP': {'method':Descriptors.MolLogP,'cutoff':5},
        'NumRotatableBonds': {'method':Lipinski.NumRotatableBonds,'cutoff':10},
        'TPSA': {'method':Chem.MolSurf.TPSA,'cutoff':140},

    }
    cont = 0
    for property in filter:
        
        if filter[property]['method'](mol) > filter[property]['cutoff']:
            cont += 1
        if cont >= maxviolation:
            return False
    return True

def lipinski_profile(mol):
    #https://www.rdkit.org/docs/source/rdkit.Chem.Lipinski.html?highlight=lipinski#module-rdkit.Chem.Lipinski
    properties = {
        'NumHAcceptors': {'method':Lipinski.NumHAcceptors,'cutoff':10},
        'NumHDonors': {'method':Lipinski.NumHDonors,'cutoff':5},
        'wt': {'method':Descriptors.MolWt,'cutoff':500},
        'MLogP': {'method':Descriptors.MolLogP,'cutoff':5},
        'NumRotatableBonds': {'method':Lipinski.NumRotatableBonds,'cutoff':10},
        'TPSA': {'method':Chem.MolSurf.TPSA,'cutoff':range(0,140)},

        'FractionCSP3': {'method':Lipinski.FractionCSP3,'cutoff':None},
        'HeavyAtomCount': {'method':Lipinski.HeavyAtomCount,'cutoff':None}, 
        'NHOHCount': {'method':Lipinski.NHOHCount,'cutoff':None},
        'NOCount': {'method':Lipinski.NOCount,'cutoff':None},
        'HeavyAtomCount': {'method':Lipinski.HeavyAtomCount,'cutoff':None},
        'NHOHCount': {'method':Lipinski.NHOHCount,'cutoff':None},
        'NOCount': {'method':Lipinski.NOCount,'cutoff':None},
        'NumAliphaticCarbocycles': {'method':Lipinski.NumAliphaticCarbocycles,'cutoff':None},
        'NumAliphaticHeterocycles': {'method':Lipinski.NumAliphaticHeterocycles,'cutoff':None},
        'NumAliphaticRings': {'method':Lipinski.NumAliphaticRings,'cutoff':None},
        'NumAromaticCarbocycles': {'method':Lipinski.NumAromaticCarbocycles,'cutoff':None},
        'NumAromaticHeterocycles': {'method':Lipinski.NumAromaticHeterocycles,'cutoff':None},
        'NumAromaticRings': {'method':Lipinski.NumAromaticRings,'cutoff':None},
        'NumHeteroatoms': {'method':Lipinski.NumHeteroatoms,'cutoff':None},
        'NumSaturatedCarbocycles': {'method':Lipinski.NumSaturatedCarbocycles,'cutoff':None},
        'NumSaturatedHeterocycles': {'method':Lipinski.NumSaturatedHeterocycles,'cutoff':None},
        'NumSaturatedRings': {'method':Lipinski.NumSaturatedRings,'cutoff':None},
        'RingCount': {'method':Lipinski.RingCount,'cutoff':None},
    }
    profile = {}
    for property in properties:
        profile[property] = properties[property]['method'](mol)
        #print(f"{property}: {properties[property]['method'](mol)}. cutoff: {properties[property]['cutoff']}")
    return profile

#===================================================================

#                        Desirability
# doi:10.1016/j.chemolab.2011.04.004; https://www.youtube.com/watch?v=quz4NW0uIYw&list=PL6ebkIZFT4xXiVdpOeKR4o_sKLSY0aQf_&index=3
#===================================================================
def LargerTheBest(Value, LowerLimit, Target, r = 1):
    if Value < LowerLimit:
        return 0.0
    elif LowerLimit <= Value <= Target:
        return ((Value -LowerLimit)/(Target-LowerLimit))**r
    else:
        return 1.0

def SmallerTheBest(Value, Target, UpperLimit, r = 1):
    """ Smaller-The-Best (STB
    """
    if Value < Target:
        return 1.0
    elif Target <= Value <= UpperLimit:
        return ((UpperLimit-Value)/(UpperLimit-Target))**r
    else:
        return 0.0

def NominalTheBest(Value, LowerLimit, Target, UpperLimit, r1 = 1, r2 = 1):
    """ Nominal-The-Best (NTB): the value of the estimated response is
    expected to achieve a particular target value (T).
    """
    if Value < LowerLimit:
        return 0.0
    elif LowerLimit <= Value <= Target:
        return ((Value -LowerLimit)/(Target-LowerLimit))**r1
    elif Target <= Value <= UpperLimit:
        return ((UpperLimit-Value)/(UpperLimit-Target))**r2
    else:
        return 0.0


# Saving data
def full_pickle(title:str, data:object):
    """Normal pickle.

    Args:
        title (str): name of the file without extension, .pkl will be added by default.
        data (object): Any serializable python object
    """
    with open(f'{title}.pkl', 'wb') as pkl:
        pickle.dump(data, pkl)

def loosen(file):
    """Unpickle a pickled object.

    Args:
        file (path): The path to the file who store the pickle object.

    Returns:
        object: The python object.
    """
    with open(file, 'rb') as pkl:
        data = pickle.load(pkl)
    return data

def compressed_pickle(title:str, data:object):
    """Compress python object. First cPickle it and then bz2.BZ2File compressed it.

    Args:
        title (str): Name of the file without extensions, .pbz2 will be added by default
        data (object): Any serializable python object
    """
    with bz2.BZ2File(f'{title}.pbz2', 'w') as f: 
        cPickle.dump(data, f)   

def decompress_pickle(file):
    """Decompress CPickle objects compressed first with bz2 formats

    Args:
        file (path): This is the cPickle files compressed with bz2.BZ2File. (as a convention with extension .pbz2, but not needed)

    Returns:
        object: The python object.
    """
    data = bz2.BZ2File(file, 'rb')
    data = cPickle.load(data)
    return data  

if __name__ == '__main__':
    pass
    # import pandas as pd
    # initial_smiles = 'COC(=O)C=1C=CC(=CC1)S(=O)(=O)N'
    # i = Individual(initial_smiles)
    # ii = Individual('O=C(Nc1ccon1)c1ccc(C(=O)/C=C(\O)C(F)(F)C(F)(F)F)c(O)c1')
    # # print(Descriptors.MolLogP(Chem.MolFromSmiles('O=C(Nc1ccon1)c1ccc(C(=O)/C=C(\O)C(F)(F)C(F)(F)F)c(O)c1')))
    # new = i.__dict__.copy()
    # del new['mol']
    # print(new.keys())
