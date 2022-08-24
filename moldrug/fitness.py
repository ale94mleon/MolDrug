#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from copy import deepcopy
from moldrug import utils
from rdkit import Chem
from rdkit.Chem import QED, Descriptors, AllChem, rdFMCS
import os, argparse
import numpy as np
from typing import Dict, List, Optional
import warnings, tempfile
from meeko import MoleculePreparation
from tqdm import tqdm
from copy import deepcopy
import Bio.PDB as PDB


#=======================================================================
"""
For the functions: duplicate_conformers, get_mcs, generate_conformers, constraintconf and constraintconf_cmd
and the class ProteinLigandClashFilter:
    Code borrowed from Pat Walters
    https://github.com/PatWalters/fragment_expansion/blob/master/rdkit_eval/rd_gen_restricted_confs.py
    Which was borrowed from Joshua Meyers
    https://github.com/JoshuaMeyers/Snippets/blob/master/200405_constrained_conformers.ipynb
    and that code was adapted from Tim Dudgeon
    https://github.com/InformaticsMatters/pipelines/blob/master/src/python/pipelines/rdkit/constrained_conf_gen.py
    All I've done is change the commandline wrapper and modify how to remove conformers that clash with the protein
"""

def duplicate_conformers(m: Chem.rdchem.Mol, new_conf_idx: int, rms_limit: float = 0.5) -> bool:
    rmslist = []
    for i in range(m.GetNumConformers()):
        if i == new_conf_idx:
            continue
        rms = AllChem.GetConformerRMS(m, new_conf_idx, i, prealigned=True)
        rmslist.append(rms)
    return any(i < rms_limit for i in rmslist)

def get_mcs(mol_one: Chem.rdchem.Mol, mol_two: Chem.rdchem.Mol) -> str:
    """Code to find the maximum common substructure between two molecules."""
    return Chem.MolToSmiles(
        Chem.MolFromSmarts(
            rdFMCS.FindMCS([mol_one, mol_two], completeRingsOnly=True, matchValences=True).smartsString
        )
    )

def generate_conformers(mol: Chem.rdchem.Mol,
                        ref_mol: Chem.rdchem.Mol,
                        num_conf: int,
                        ref_smi: str = None,
                        minimum_conf_rms: Optional[float] = None,
                        ) -> List[Chem.rdchem.Mol]:
    # if SMILES to be fixed are not given, assume to the MCS
    if not ref_smi:
        ref_smi = get_mcs(mol, ref_mol)

    # Creating core of reference ligand #
    core_with_wildcards = AllChem.ReplaceSidechains(ref_mol, Chem.MolFromSmiles(ref_smi))
    core1 = AllChem.DeleteSubstructs(core_with_wildcards, Chem.MolFromSmiles('*'))
    core1.UpdatePropertyCache()

    # Add Hs so that conf gen is improved
    mol.RemoveAllConformers()
    outmol = deepcopy(mol)
    mol_wh = Chem.AddHs(mol)

    # Generate conformers with constrained embed
    dup_count = 0
    for i in range(num_conf):
        temp_mol = Chem.Mol(mol_wh)  # copy to avoid inplace changes
        AllChem.ConstrainedEmbed(temp_mol, core1, randomseed=i)
        temp_mol = Chem.RemoveHs(temp_mol)
        conf_idx = outmol.AddConformer(temp_mol.GetConformer(0), assignId=True)
        if minimum_conf_rms is not None:
            if duplicate_conformers(outmol, conf_idx, rms_limit=minimum_conf_rms):
                dup_count += 1
                outmol.RemoveConformer(conf_idx)
    if dup_count:
        pass
    # print(f'removed {dup_count} duplicated conformations')
    return outmol


class ProteinLigandClashFilter:
    def __init__(self, protein_pdbpath: str, distance: float = 1.5):
        parser = PDB.PDBParser(QUIET=True, PERMISSIVE=True)
        s = parser.get_structure('protein', protein_pdbpath)
        self.kd = PDB.NeighborSearch(list(s.get_atoms()))
        self.radius = distance

    def __call__(self, conf: Chem.rdchem.Conformer) -> bool:
        for coord in conf.GetPositions():
            res = self.kd.search(coord, radius=self.radius)
            if len(res):
                return True
        return False

def constraintconf(pdb:str, smi:str, fix:str, out:str, max:int = 25, rms:float = 0.01, bump:float = 1.5):
    """_summary_

    Parameters
    ----------
    pdb : str
        Protein pdb file
    smi : str
        Input SMILES file name
    fix : str
        File with fixed piece of the molecule
    out : str
        Output file name
    max : int, optional
        Maximum number of conformers to generate, by default 25
    rms : float, optional
        RMS cutoff, by default 0.01
    bump : float, optional
        Bump cutoff, by default 1.5
    """

    ref = Chem.MolFromMolFile(fix)
    suppl = Chem.SmilesMolSupplier(smi, titleLine=False)
    writer = Chem.SDWriter(out)

    clash_filter = ProteinLigandClashFilter(pdb, distance=bump)

    for mol in tqdm(suppl):
        # generate conformers
        out_mol = generate_conformers(mol, ref,
                                      max,
                                      ref_smi=Chem.MolToSmiles(ref),
                                      minimum_conf_rms=rms)

        # remove conformers that clash with the protein
        clashIds = [conf.GetId() for conf in out_mol.GetConformers() if clash_filter(conf)]
        [out_mol.RemoveConformer(clashId) for clashId in clashIds]

        # write out the surviving conformers
        for conf in out_mol.GetConformers():
            writer.write(out_mol, confId=conf.GetId())

def constraintconf_cmd():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '--pdb',
        help = 'Protein pdb file',
        dest = 'pdb',
        type = str,
    )
    parser.add_argument(
        '--smi',
        help='Input SMILES file name',
        dest = 'smi',
        type = str,
    )
    parser.add_argument(
        '--fix',
        help = 'File with fixed piece of the molecule',
        dest = 'fix',
        type = str,
    )
    parser.add_argument(
        '--out',
        help = 'Output file name',
        dest = 'out',
        type = str,
    )
    parser.add_argument(
        '--max',
        help = 'Maximum number of conformers to generate, by default %(default)s',
        dest = 'max',
        default = 25,
        type = int,
    )
    parser.add_argument(
        '--rms',
        help = 'RMS cutoff, by default %(default)s',
        dest = 'rms',
        default = 0.01,
        type = float,
    )
    parser.add_argument(
        '--bump',
        help = 'Bump cutoff, by default %(default)s',
        dest = 'bump',
        default = 1.5,
        type = float,
    )
    args = parser.parse_args()
    constraintconf(args.pdb, args.smi, args.fix, args.out, args.max, args.rms, args.bump)
#=======================================================================

def vinadock(
    Individual:utils.Individual,
    wd:str = '.vina_jobs',
    vina_executable:str = 'vina',
    receptor_pdbqt_path:str = None,
    boxcenter:List[float] = None,
    boxsize:List[float] = None,
    exhaustiveness:int = 8,
    ncores:int = 1,
    num_modes:int = 1,
    constraint:bool = False, 
    constraint_type = 'score_only', # score_only, local_only
    constraint_ref:Chem.rdchem.Mol = None,
    constraint_receptor_pdb_path:str = None,
    constraint_num_conf:int = 100,
    constraint_minimum_conf_rms:int = 0.01):
    # Creating the command line for vina
    cmd_vina_str = f"{vina_executable} --receptor {receptor_pdbqt_path}"\
        f" --center_x {boxcenter[0]} --center_y {boxcenter[1]} --center_z {boxcenter[2]}"\
        f" --size_x {boxsize[0]} --size_y {boxsize[1]} --size_z {boxsize[2]}"\
        f" --cpu {ncores} --exhaustiveness {exhaustiveness} --num_modes {num_modes}"
    
    if constraint:
        # Check for the correct type of docking
        if constraint_type in ['score_only', 'local_only']:
            cmd_vina_str += f" --{constraint_type}"
        else:
            raise Exception(f"constraint_type only admit two possible values: score_only, local_only.")
    
        # Generate constrained conformer
        out_mol = generate_conformers(
            mol = Chem.RemoveHs(Individual.mol), 
            ref_mol = Chem.RemoveHs(constraint_ref),
            num_conf = constraint_num_conf,
            #ref_smi=Chem.MolToSmiles(constraint_ref),
            minimum_conf_rms=constraint_minimum_conf_rms)

        # Remove conformers that clash with the protein
        clash_filter = ProteinLigandClashFilter(protein_pdbpath = constraint_receptor_pdb_path, distance=1.5)
        clashIds = [conf.GetId() for conf in out_mol.GetConformers() if clash_filter(conf)]
        [out_mol.RemoveConformer(clashId) for clashId in clashIds]

        vina_score_pdbqt = (np.inf, Individual.pdbqt)
        for conf in out_mol.GetConformers():
            temp_mol = deepcopy(out_mol)
            temp_mol.RemoveAllConformers()
            temp_mol.AddConformer(out_mol.GetConformer(conf.GetId()), assignId=True)

            preparator = MoleculePreparation()
            preparator.prepare(temp_mol)
            preparator.write_pdbqt_file(os.path.join(wd, f'{Individual.idx}_conf_{conf.GetId()}.pdbqt'))

            # Make a copy to the vina command string and add the out (is needed) and ligand options
            cmd_vina_str_tmp = cmd_vina_str[:]
            cmd_vina_str_tmp += f" --ligand {os.path.join(wd, f'{Individual.idx}_conf_{conf.GetId()}.pdbqt')}"
            if constraint_type == 'local_only':
                cmd_vina_str_tmp += f" --out {os.path.join(wd, f'{Individual.idx}_conf_{conf.GetId()}_out.pdbqt')}"

            try:
                cmd_vina_result = utils.run(cmd_vina_str_tmp)
            except Exception as e:
                if os.path.isfile(receptor_pdbqt_path):
                    with open(receptor_pdbqt_path, 'r') as f:
                        receptor_str = f.read()
                else:
                    receptor_str = None

                error = {
                    'Exception': e,
                    'Individual': Individual,
                    f'used_mol_conf_{conf.GetId()}': temp_mol,
                    f'used_ligand_pdbqt_conf_{conf.GetId()}': preparator.write_pdbqt_string(),
                    'receptor_str': receptor_str,
                    'boxcenter': boxcenter,
                    'boxsize': boxsize,
                }
                utils.compressed_pickle(f'{Individual.idx}_conf_{conf.GetId()}_error', error)
                warnings.warn(f"Dear user, as you know MolDrug is still in development and need your help to improve."\
                    f"For some reason vina fails and prompts the following error: {e}. In the directory {os.getcwd()} there is file called {Individual.idx}_conf_{i}_error.pbz2"\
                    "Please, if you don't figure it out what could be the problem, please open an issue in https://github.com/ale94mleon/MolDrug/issues. We will try to help you"\
                    "Have at hand the file error.pbz2, we will needed to try to understand the error. The file has the following info: the exception, the current Individual, the receptor pdbqt string as well the definition of the box.")
                vina_score_pdbqt = (np.inf, preparator.write_pdbqt_string())
                return vina_score_pdbqt

            for line in cmd_vina_result.stdout.split('\n'):
                if line.startswith('Affinity'):
                    vina_score = float(line.split()[1])
                    break
            if vina_score < vina_score_pdbqt[0]:
                if constraint_type == 'local_only':
                    best_energy = utils.VINA_OUT(os.path.join(wd, f'{Individual.idx}_conf_{conf.GetId()}_out.pdbqt')).BestEnergy()
                    vina_score_pdbqt = (vina_score, ''.join(best_energy.chunk))
                else:
                    vina_score_pdbqt = (vina_score, preparator.write_pdbqt_string())
    # "Normal" docking
    else:
        cmd_vina_str += f" --ligand {os.path.join(wd, f'{Individual.idx}.pdbqt')} --out {os.path.join(wd, f'{Individual.idx}_out.pdbqt')}"
        with open(os.path.join(wd, f'{Individual.idx}.pdbqt'), 'w') as l:
            l.write(Individual.pdbqt)
        try:
            utils.run(cmd_vina_str)
        except Exception as e:
            if os.path.isfile(receptor_pdbqt_path):
                with open(receptor_pdbqt_path, 'r') as f:
                    receptor_str = f.read()
            else:
                receptor_str = None

            error = {
                'Exception': e,
                'Individual': Individual,
                'receptor_str': receptor_str,
                'boxcenter': boxcenter,
                'boxsize': boxsize,
            }
            utils.compressed_pickle(f'{Individual.idx}_error', error)
            warnings.warn(f"Dear user, as you know MolDrug is still in development and need your help to improve."\
                f"For some reason vina fails and prompts the following error: {e}. In the directory {os.getcwd()} there is file called {Individual.idx}_error.pbz2"\
                "Please, if you don't figure it out what could be the problem, please open an issue in https://github.com/ale94mleon/MolDrug/issues. We will try to help you"\
                "Have at hand the file error.pbz2, we will needed to try to understand the error. The file has the following info: the exception, the current Individual, the receptor pdbqt string as well the definition of the box.")

            vina_score_pdbqt = (np.inf, Individual.pdbqt)
            return vina_score_pdbqt

        # Getting the information
        best_energy = utils.VINA_OUT(os.path.join(wd, f'{Individual.idx}_out.pdbqt')).BestEnergy()
        vina_score_pdbqt = (best_energy.freeEnergy, ''.join(best_energy.chunk))
    return vina_score_pdbqt


def Cost(
    Individual:utils.Individual,
    wd:str = '.vina_jobs',
    vina_executable:str = 'vina',
    receptor_pdbqt_path:str = None,
    boxcenter:List[float] = None,
    boxsize:List[float] =None,
    exhaustiveness:int = 8,
    ncores:int = 1,
    num_modes:int = 1,
    constraint:bool = False, 
    constraint_type = 'score_only', # score_only, local_only
    constraint_ref:Chem.rdchem.Mol = None,
    constraint_receptor_pdb_path:str = None,
    constraint_num_conf:int = 100,
    constraint_minimum_conf_rms:int = 0.01,
    desirability:Dict = {
        'qed': {
            'w': 1,
            'LargerTheBest': {
                'LowerLimit': 0.1,
                'Target': 0.75,
                'r': 1
            }
        },
        'sa_score': {
            'w': 1,
            'SmallerTheBest': {
                'Target': 3,
                'UpperLimit': 7,
                'r': 1
            }
        },
        'vina_score': {
            'w': 1,
            'SmallerTheBest': {
                'Target': -12,
                'UpperLimit': -6,
                'r': 1
            }
        }
    }
    ):
    """This is the main Cost function of the module. It use the concept of desirability functions. The response variables are:

    #. `Vina score. <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3041641/>`_
    #. `Quantitative Estimation of Drug-likeness (QED). <https://www.nature.com/articles/nchem.1243>`_
    #. `Synthetic accessibility score.  <https://jcheminf.biomedcentral.com/articles/10.1186/1758-2946-1-8)>`_

    Parameters
    ----------
    Individual : utils.Individual
        A Individual with the pdbqt attribute
    wd : str, optional
        The working directory to execute the docking jobs, by default '.vina_jobs'
    vina_executable : str, optional
        This is the name of the vina executable, could be a path to the binary object (x, y, z),  by default 'vina'
    receptor_path : str, optional
        Where the receptor pdbqt file is located, by default None
    boxcenter : list[float], optional
        A list of three floats with the definition of the center of the box in angstrom for docking (x, y, z), by default None
    boxsize : list[float], optional
        A list of three floats with the definition of the box size in angstrom of the docking box (x, y, z), by default None
    exhaustiveness : int, optional
        Parameter of vina that controls the accuracy of the docking searching, by default 8
    ncores : int, optional
        Number of cpus to use in Vina, by default 1
    num_modes : int, optional
        How many modes should Vina export, by default 1
    desirability : dict, optional
        The definition of the desirability to use for each used variable = [qed, sa_score, vina_score].
        Each variable only will accept the keys [w, and the name of the desirability function of :meth:`moldrug.utils.DerringerSuichDesirability`]
        ,by default { 'qed': { 'w': 1, 'LargerTheBest': { 'LowerLimit': 0.1, 'Target': 0.75, 'r': 1 } }, 'sa_score': { 'w': 1, 'SmallerTheBest': { 'Target': 3, 'UpperLimit': 7, 'r': 1 } }, 'vina_score': { 'w': 1, 'SmallerTheBest': { 'Target': -12, 'UpperLimit': -6, 'r': 1 } } }

    Returns
    -------
    utils.Individual
        A new instance of the original Individual with the the new attributes: pdbqt, qed, vina_score, sa_score and cost. cost attribute will be a number between 0 and 1, been 0 the optimal value.
    Example
    -------
    .. ipython:: python

        from moldrug import utils, fitness
        from rdkit import Chem
        import tempfile, os
        from moldrug.data import ligands, boxes, receptor_pdbqt
        tmp_path = tempfile.TemporaryDirectory()
        ligand_mol = Chem.MolFromSmiles(ligands.r_x0161)
        I = utils.Individual(ligand_mol)
        receptor_path = os.path.join(tmp_path.name,'receptor.pdbqt')
        with open(receptor_path, 'w') as r: r.write(receptor_pdbqt.r_x0161)
        box = boxes.r_x0161['A']
        # Using the default desirability
        NewI = fitness.Cost(Individual = I,wd = tmp_path.name,receptor_pdbqt_path = receptor_path,boxcenter = box['boxcenter'],boxsize = box['boxsize'],exhaustiveness = 4,ncores = 4)
        print(NewI.cost, NewI.vina_score, NewI.qed, NewI.sa_score)
    """
    sascorer = utils.import_sascorer()
    # multicriteria optimization,Optimization of Several Response Variables
    # Getting estimate of drug-likness
    Individual.qed = QED.weights_mean(Individual.mol)

    # Getting synthetic accessibility score
    Individual.sa_score = sascorer.calculateScore(Individual.mol)

    # Getting vina_score and update pdbqt
    Individual.vina_score, Individual.pdbqt = vinadock(
        Individual = Individual,
        wd = wd,
        vina_executable = vina_executable,
        receptor_pdbqt_path =  receptor_pdbqt_path,
        boxcenter = boxcenter,
        boxsize = boxsize,
        exhaustiveness = exhaustiveness,
        ncores = ncores,
        num_modes = num_modes,
        constraint = constraint, 
        constraint_type = constraint_type,
        constraint_ref = constraint_ref,
        constraint_receptor_pdb_path = constraint_receptor_pdb_path,
        constraint_num_conf = constraint_num_conf,
        constraint_minimum_conf_rms = constraint_minimum_conf_rms,
    )
    # Adding the cost using all the information of qed, sas and vina_cost
    # Construct the desirability
    # Quantitative estimation of drug-likness (ranges from 0 to 1). We could use just the value perse, but using LargerTheBest we are more permissible.

    base = 1
    exponent = 0
    for variable in desirability:
        for key in desirability[variable]:
            if key == 'w':
                w = desirability[variable][key]
            elif key in utils.DerringerSuichDesirability():
                d = utils.DerringerSuichDesirability()[key](getattr(Individual, variable), **desirability[variable][key])
            else:
                raise RuntimeError(f"Inside the desirability dictionary you provided for the variable = {variable} a non implemented key = {key}. Only are possible: 'w' (standing for weight) and any possible Derringer-Suich desirability function: {utils.DerringerSuichDesirability().keys()}")
        base *= d**w
        exponent += w
    # Average
    #D = (w_qed*d_qed + w_sa_score*d_sa_score + w_vina_score*d_vina_score) / (w_qed + w_sa_score + w_vina_score)
    # Geometric mean
    # D = (d_qed**w_qed * d_sa_score**w_sa_score * d_vina_score**w_vina_score)**(1/(w_qed + w_sa_score + w_vina_score))
    # We are using Geometric mean
    D = base**(1/exponent)
    #  And because we are minimizing we have to return
    Individual.cost = 1 - D
    return Individual

def CostOnlyVina(
    Individual:utils.Individual,
    wd:str = '.vina_jobs',
    vina_executable:str = 'vina',
    receptor_pdbqt_path:str = None,
    boxcenter:List[float] = None,
    boxsize:List[float] =None,
    exhaustiveness:int = 8,
    ncores:int = 1,
    num_modes:int = 1,
    constraint:bool = False, 
    constraint_type = 'score_only', # score_only, local_only
    constraint_ref:Chem.rdchem.Mol = None,
    constraint_receptor_pdb_path:str = None,
    constraint_num_conf:int = 100,
    constraint_minimum_conf_rms:int = 0.01,
    wt_cutoff:float = None,
    ):
    """This Cost function performs Docking and return the vina_score as cost.

    Parameters
    ----------
    Individual : utils.Individual
        A Individual with the pdbqt attribute
    wd : str, optional
        The working directory to execute the docking jobs, by default '.vina_jobs'
    vina_executable : str, optional
        This is the name of the vina executable, could be a path to the binary object (x, y, z),  by default 'vina'
    receptor_path : str, optional
        Where the receptor pdbqt file is located, by default None
    boxcenter : list[float], optional
        A list of three floats with the definition of the center of the box in angstrom for docking (x, y, z), by default None
    boxsize : list[float], optional
        A list of three floats with the definition of the box size in angstrom of the docking box (x, y, z), by default None
    exhaustiveness : int, optional
        Parameter of vina that controls the accuracy of the docking searching, by default 8
    ncores : int, optional
        Number of cpus to use in Vina, by default 1
    num_modes : int, optional
        How many modes should Vina export, by default 1
    desirability : dict, optional
        The definition of the desirability to use for each used variable = [qed, sa_score, vina_score].
        Each variable only will accept the keys [w, and the name of the desirability function of :meth:`moldrug.utils.DerringerSuichDesirability`]
        ,by default { 'qed': { 'w': 1, 'LargerTheBest': { 'LowerLimit': 0.1, 'Target': 0.75, 'r': 1 } }, 'sa_score': { 'w': 1, 'SmallerTheBest': { 'Target': 3, 'UpperLimit': 7, 'r': 1 } }, 'vina_score': { 'w': 1, 'SmallerTheBest': { 'Target': -12, 'UpperLimit': -6, 'r': 1 } } }
    wt_cutoff : float, optional
        If some number is provided the molecules with a molecular weight higher than wt_cutoff will get as vina_score = cost = np.inf. Vina will not be invoked, by default None
    Returns
    -------
    utils.Individual
        A new instance of the original Individual with the the new attributes: pdbqt, vina_score and cost. In this case cost = vina_score, the lowest the values the best individual.
    Example
    -------
    .. ipython:: python

        from moldrug import utils, fitness
        from rdkit import Chem
        import tempfile, os
        from moldrug.data import ligands, boxes, receptor_pdbqt
        tmp_path = tempfile.TemporaryDirectory()
        ligand_mol = Chem.MolFromSmiles(ligands.r_x0161)
        I = utils.Individual(ligand_mol)
        receptor_path = os.path.join(tmp_path.name,'receptor.pdbqt')
        with open(receptor_path, 'w') as r: r.write(receptor_pdbqt.r_x0161)
        box = boxes.r_x0161['A']
        NewI = fitness.CostOnlyVina(Individual = I,wd = tmp_path.name,receptor_pdbqt_path = receptor_path,boxcenter = box['boxcenter'],boxsize = box['boxsize'],exhaustiveness = 4,ncores = 4)
        print(NewI.cost, NewI.vina_score)
    """
    # If the molecule is heavy, don't perform docking and assign infinite to the cost attribute. Add the pdbqt to pdbqts and np.inf to vina_scores
    if wt_cutoff:
        if Descriptors.MolWt(Individual.mol) > wt_cutoff:
            Individual.vina_score = np.inf
            Individual.cost = np.inf
            return Individual

    # Getting vina_score and update pdbqt
    Individual.vina_score, Individual.pdbqt = vinadock(
        Individual = Individual,
        wd = wd,
        vina_executable = vina_executable,
        receptor_pdbqt_path =  receptor_pdbqt_path,
        boxcenter = boxcenter,
        boxsize = boxsize,
        exhaustiveness = exhaustiveness,
        ncores = ncores,
        num_modes = num_modes,
        constraint = constraint, 
        constraint_type = constraint_type,
        constraint_ref = constraint_ref,
        constraint_receptor_pdb_path = constraint_receptor_pdb_path,
        constraint_num_conf = constraint_num_conf,
        constraint_minimum_conf_rms = constraint_minimum_conf_rms,
    )
    Individual.cost = Individual.vina_score
    return Individual



def CostMultiReceptors(
    Individual:utils.Individual,
    wd:str = '.vina_jobs',
    vina_executable:str = 'vina',
    receptor_pdbqt_path:List[str] = None,
    vina_score_type:List[str] = None,
    boxcenter:List[float] = None,
    boxsize:List[float] =None,
    exhaustiveness:int = 8,
    ncores:int = 1,
    num_modes:int = 1,
    constraint:bool = False, 
    constraint_type = 'score_only', # score_only, local_only
    constraint_ref:List[Chem.rdchem.Mol] = None,
    constraint_receptor_pdb_path:List[str] = None,
    constraint_num_conf:int = 100,
    constraint_minimum_conf_rms:int = 0.01,
    desirability:Dict = {
        'qed': {
            'w': 1,
            'LargerTheBest': {
                'LowerLimit': 0.1,
                'Target': 0.75,
                'r': 1
            }
        },
        'sa_score': {
            'w': 1,
            'SmallerTheBest': {
                'Target': 3,
                'UpperLimit': 7,
                'r': 1
            }
        },
        'vina_scores': {
            'min':{
                'w': 1,
                'SmallerTheBest': {
                    'Target': -12,
                    'UpperLimit': -6,
                    'r': 1
                }
            },
            'max':{
                'w': 1,
                'LargerTheBest': {
                    'LowerLimit': -4,
                    'Target': 0,
                    'r': 1
                }
            }
        }
    }
    ):
    """This function is similar to :meth:`moldrug.fitness.Cost` but it will add the possibility to work with more than one receptor. It also use the concept of desirability and the response variables are:

    #. `Vina scores. <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3041641/>`_
    #. `Quantitative Estimation of Drug-likeness (QED). <https://www.nature.com/articles/nchem.1243>`_
    #. `Synthetic accessibility score.  <https://jcheminf.biomedcentral.com/articles/10.1186/1758-2946-1-8)>`_

    In this case every vina score (for all the provided receptors) will be used for the construction of the desirability.

    Parameters
    ----------
    Individual : utils.Individual
        A Individual with the pdbqt attribute
    wd : str, optional
        The working directory to execute the docking jobs, by default '.vina_jobs'
    vina_executable : str, optional
        This is the name of the vina executable, could be a path to the binary object (x, y, z), by default 'vina'
    receptor_pdbqt_path : list[str], optional
        A list of location of the receptors pdbqt files, by default None
    vina_score_types : list[str], optional
        This is a list with the keywords 'min' and/or 'max'. E.g. If two receptor were provided and for the first one we would like to find a minimum in the vina scoring function and for the other one a maximum (selectivity for the first receptor); we must provided the list: ['min', 'max'], by default None
    boxcenter : list[float], optional
        A list of three floats with the definition of the center of the box in angstrom for docking (x, y, z), by default None
    boxsize : list[float], optional
        A list of three floats with the definition of the box size in angstrom of the docking box (x, y, z), by default None
    exhaustiveness : int, optional
        Parameter of vina that controls the accuracy of the docking searching, by default 8
    ncores : int, optional
         Number of cpus to use in Vina, by default 1
    num_modes : int, optional
        How many modes should Vina export, by default 1
    desirability : dict, optional
        The definition of the desirability to use for each used variable = [qed, sa_score, vina_scores].
        Each variable only will accept the keys [w, and the name of the desirability function of :meth:`moldrug.utils.DerringerSuichDesirability`].
        In the case of vina_scores there is another layer for the vina_score_type= [min, max],
        by default { 'qed': { 'w': 1, 'LargerTheBest': { 'LowerLimit': 0.1, 'Target': 0.75, 'r': 1 } }, 'sa_score': { 'w': 1, 'SmallerTheBest': { 'Target': 3, 'UpperLimit': 7, 'r': 1 } }, 'vina_score': { 'min':{ 'w': 1, 'SmallerTheBest': { 'Target': -12, 'UpperLimit': -6, 'r': 1 } }, 'max':{ 'w': 1, 'LargerTheBest': { 'LowerLimit': -4, 'Target': 0, 'r': 1 } } } }

    Returns
    -------
    utils.Individual
        A new instance of the original Individual with the the new attributes: pdbqts [a list of pdbqt], qed, vina_scores [a list of vina_score], sa_score and cost. cost attribute will be a number between 0 and 1, been 0 the optimal value.

    Example
    -------
    .. ipython:: python

        from moldrug import utils, fitness
        from rdkit import Chem
        import tempfile, os
        from moldrug.data import ligands, boxes, receptor_pdbqt
        tmp_path = tempfile.TemporaryDirectory()
        ligand_mol = Chem.MolFromSmiles(ligands.r_x0161)
        I = utils.Individual(ligand_mol)
        receptor_paths = [os.path.join(tmp_path.name,'receptor1.pdbqt'),os.path.join(tmp_path.name,'receptor2.pdbqt')]
        with open(receptor_paths[0], 'w') as r: r.write(receptor_pdbqt.r_x0161)
        with open(receptor_paths[1], 'w') as r: r.write(receptor_pdbqt.r_6lu7)
        boxcenter = [boxes.r_x0161['A']['boxcenter'], boxes.r_6lu7['A']['boxcenter']]
        boxsize = [boxes.r_x0161['A']['boxsize'], boxes.r_6lu7['A']['boxsize']]
        vina_score_type = ['min', 'max']
        # Using the default desirability
        NewI = fitness.CostMultiReceptors(Individual = I,wd = tmp_path.name,receptor_pdbqt_path = receptor_paths, vina_score_type = vina_score_type, boxcenter = boxcenter,boxsize = boxsize,exhaustiveness = 4,ncores = 4)
        print(NewI.cost, NewI.vina_score, NewI.qed, NewI.sa_score)
    """
    sascorer = utils.import_sascorer()
    Individual.qed = QED.weights_mean(Individual.mol)

    # Getting synthetic accessibility score
    Individual.sa_score = sascorer.calculateScore(Individual.mol)

    # Getting Vina score
    pdbqt_list = []
    Individual.vina_score = []
    for i in range(len(receptor_pdbqt_path)):
    # Getting vina_score and update pdbqt
        if constraint:
            vina_score, pdbqt = vinadock(
                Individual = Individual,
                wd = wd,
                vina_executable = vina_executable,
                receptor_pdbqt_path =  receptor_pdbqt_path[i],
                boxcenter = boxcenter[i],
                boxsize = boxsize[i],
                exhaustiveness = exhaustiveness,
                ncores = ncores,
                num_modes = num_modes,
                constraint = constraint, 
                constraint_type = constraint_type,
                constraint_ref = constraint_ref[i],
                constraint_receptor_pdb_path = constraint_receptor_pdb_path[i],
                constraint_num_conf = constraint_num_conf,
                constraint_minimum_conf_rms = constraint_minimum_conf_rms,
            )
        else:
            vina_score, pdbqt = vinadock(
                Individual = Individual,
                wd = wd,
                vina_executable = vina_executable,
                receptor_pdbqt_path =  receptor_pdbqt_path[i],
                boxcenter = boxcenter[i],
                boxsize = boxsize[i],
                exhaustiveness = exhaustiveness,
                ncores = ncores,
                num_modes = num_modes,
            )
        Individual.vina_score.append(vina_score)
        pdbqt_list.append(pdbqt)
    # Update the pdbqt attribute
    Individual.pdbqt = pdbqt_list

    # make a copy of the default values of desirability
    # pops the region of vina_scores
    desirability_to_work_with = desirability.copy()
    vina_desirability_section = desirability_to_work_with.pop('vina_scores')
    # Initialize base and exponent
    base = 1
    exponent = 0
    # Runs for all properties different to vina_scores
    for variable in desirability_to_work_with:
        for key in desirability_to_work_with[variable]:
            if key == 'w':
                w = desirability_to_work_with[variable][key]
            elif key in utils.DerringerSuichDesirability():
                d = utils.DerringerSuichDesirability()[key](getattr(Individual, variable), **desirability_to_work_with[variable][key])
            else:
                raise RuntimeError(f"Inside the desirability dictionary you provided for the variable = {variable} a non implemented key = {key}. Only are possible: 'w' (standing for weight) and any possible Derringer-Suich desirability function: {utils.DerringerSuichDesirability().keys()}. Only in the case of vina_scores [min and max] keys")
        base *= d**w
        exponent += w

    # Run only for vina_scores
    for vs, vst in zip(Individual.vina_score, vina_score_type):
        for key in vina_desirability_section[vst]:
            if key == 'w':
                w = vina_desirability_section[vst][key]
            elif key in utils.DerringerSuichDesirability():
                d = utils.DerringerSuichDesirability()[key](vs, **vina_desirability_section[vst][key])
            else:
                raise RuntimeError(f"Inside the desirability dictionary you provided for the variable = vina_scores[{vst}] a non implemented key = {key}. Only are possible: 'w' (standing for weight) and any possible Derringer-Suich desirability function: {utils.DerringerSuichDesirability().keys()}.")
        base *= d**w
        exponent += w

    # Average
    #D = (w_qed*d_qed + w_sa_score*d_sa_score + sum([w_vina_score*d_vina_score for w_vina_score, d_vina_score in zip(w_vina_scores, d_vina_scores)])) / (w_qed + w_sa_score + sum(w_vina_scores))
    # Geometric mean
    # D = (d_qed**w_qed * d_sa_score**w_sa_score * np.prod([d_vina_score**w_vina_score for d_vina_score, w_vina_score in zip(d_vina_scores, w_vina_scores)]))** (1/(w_qed + w_sa_score + sum(w_vina_scores)))
    D = base**(1/exponent)
    # And because we are minimizing we have to return
    Individual.cost = 1 - D
    return Individual

def CostMultiReceptorsOnlyVina(
    Individual:utils.Individual,
    wd:str = '.vina_jobs',
    vina_executable:str = 'vina',
    receptor_pdbqt_path:List[str] = None,
    vina_score_type:List[str] = None,
    boxcenter:List[float] = None,
    boxsize:List[float] =None,
    exhaustiveness:int = 8,
    ncores:int = 1,
    num_modes:int = 1,
    constraint:bool = False, 
    constraint_type = 'score_only', # score_only, local_only
    constraint_ref:List[Chem.rdchem.Mol] = None,
    constraint_receptor_pdb_path:List[str] = None,
    constraint_num_conf:int = 100,
    constraint_minimum_conf_rms:int = 0.01,
    desirability:Dict = {
        'min':{
            'w': 1,
            'SmallerTheBest': {
                'Target': -12,
                'UpperLimit': -6,
                'r': 1
            }
        },
        'max':{
            'w': 1,
            'LargerTheBest': {
                'LowerLimit': -4,
                'Target': 0,
                'r': 1
            }
        }
    },
    wt_cutoff = None,
    ):
    """This function is similar to :meth:`moldrug.fitness.CostOnlyVina` but it will add the possibility to work with more than one receptor. It also use the concept of desirability.
    The response variables are the vina scores on each receptor.

    Parameters
    ----------
    Individual : utils.Individual
        A Individual with the pdbqt attribute
    wd : str, optional
        The working directory to execute the docking jobs, by default '.vina_jobs'
    vina_executable : str, optional
        This is the name of the vina executable, could be a path to the binary object (x, y, z), by default 'vina'
    receptor_paths : list[str], optional
        A list of location of the receptors pdbqt files, by default None
    vina_score_types : list[str], optional
        This is a list with the keywords 'min' and/or 'max'. E.g. If two receptor were provided and for the first one we would like to find a minimum in the vina scoring function and for the other one a maximum (selectivity for the first receptor); we must provided the list: ['min', 'max'], by default None
    boxcenters : list[float], optional
        A list of three floats with the definition of the center of the box in angstrom for docking (x, y, z), by default None
    boxsizes : list[float], optional
        A list of three floats with the definition of the box size in angstrom of the docking box (x, y, z), by default None
    exhaustiveness : int, optional
        Parameter of vina that controls the accuracy of the docking searching, by default 8
    ncores : int, optional
         Number of cpus to use in Vina, by default 1
    num_modes : int, optional
        How many modes should Vina export, by default 1
    desirability : dict, optional
        The definition of the desirability when min or max is used.
        Each variable only will accept the keys [w, and the name of the desirability function of :meth:`moldrug.utils.DerringerSuichDesirability`].
        by default { 'min':{ 'w': 1, 'SmallerTheBest': { 'Target': -12, 'UpperLimit': -6, 'r': 1 } }, 'max':{ 'w': 1, 'LargerTheBest': { 'LowerLimit': -4, 'Target': 0, 'r': 1 } } }
    wt_cutoff : float, optional
        If some number is provided the molecules with a molecular weight higher than wt_cutoff will get as vina_score = cost = np.inf. Vina will not be invoked, by default None

    Returns
    -------
    utils.Individual
        A new instance of the original Individual with the the new attributes: pdbqts [a list of pdbqt], vina_scores [a list of vina_score], and cost. cost attribute will be a number between 0 and 1, been 0 the optimal value.

    Example
    -------
    .. ipython:: python

        from moldrug import utils, fitness
        from rdkit import Chem
        import tempfile, os
        from moldrug.data import ligands, boxes, receptor_pdbqt
        tmp_path = tempfile.TemporaryDirectory()
        ligand_mol = Chem.MolFromSmiles(ligands.r_x0161)
        I = utils.Individual(ligand_mol)
        receptor_paths = [os.path.join(tmp_path.name,'receptor1.pdbqt'),os.path.join(tmp_path.name,'receptor2.pdbqt')]
        with open(receptor_paths[0], 'w') as r: r.write(receptor_pdbqt.r_x0161)
        with open(receptor_paths[1], 'w') as r: r.write(receptor_pdbqt.r_6lu7)
        boxcenter = [boxes.r_x0161['A']['boxcenter'], boxes.r_6lu7['A']['boxcenter']]
        boxsize = [boxes.r_x0161['A']['boxsize'], boxes.r_6lu7['A']['boxsize']]
        vina_score_type = ['min', 'max']
        # Using the default desirability
        NewI = fitness.CostMultiReceptorsOnlyVina(Individual = I,wd = tmp_path.name,receptor_pdbqt_path = receptor_paths, vina_score_type = vina_score_type, boxcenter = boxcenter,boxsize = boxsize,exhaustiveness = 4,ncores = 4)
        print(NewI.cost, NewI.vina_score)
    """
    pdbqt_list = []
    Individual.vina_score = []

    # If the molecule is heavy, don't perform docking and assign infinite to the cost attribute. Add the pdbqt to pdbqts and np.inf to vina_scores
    if wt_cutoff:
        if Descriptors.MolWt(Individual.mol) > wt_cutoff:
            for _ in range(len(receptor_pdbqt_path)):
                pdbqt_list.append(Individual.pdbqt)
                Individual.vina_score.append(np.inf)
            Individual.cost = np.inf
            # Update the pdbqt attribute
            Individual.pdbqt = pdbqt_list
            return Individual

    # Getting Vina score
    pdbqt_list = []
    Individual.vina_score = []
    for i in range(len(receptor_pdbqt_path)):
    # Getting vina_score and update pdbqt
        if constraint:
            vina_score, pdbqt = vinadock(
                Individual = Individual,
                wd = wd,
                vina_executable = vina_executable,
                receptor_pdbqt_path =  receptor_pdbqt_path[i],
                boxcenter = boxcenter[i],
                boxsize = boxsize[i],
                exhaustiveness = exhaustiveness,
                ncores = ncores,
                num_modes = num_modes,
                constraint = constraint, 
                constraint_type = constraint_type,
                constraint_ref = constraint_ref[i],
                constraint_receptor_pdb_path = constraint_receptor_pdb_path[i],
                constraint_num_conf = constraint_num_conf,
                constraint_minimum_conf_rms = constraint_minimum_conf_rms,
            )
        else:
            vina_score, pdbqt = vinadock(
                Individual = Individual,
                wd = wd,
                vina_executable = vina_executable,
                receptor_pdbqt_path =  receptor_pdbqt_path[i],
                boxcenter = boxcenter[i],
                boxsize = boxsize[i],
                exhaustiveness = exhaustiveness,
                ncores = ncores,
                num_modes = num_modes,
            )
        Individual.vina_score.append(vina_score)
        pdbqt_list.append(pdbqt)
    # Update the pdbqt attribute
    Individual.pdbqt = pdbqt_list

    # Initialize base and exponent
    base = 1
    exponent = 0
    # Run for vina_scores
    for vs, vst in zip(Individual.vina_score, vina_score_type):
        for key in desirability[vst]:
            if key == 'w':
                w = desirability[vst][key]
            elif key in utils.DerringerSuichDesirability():
                d = utils.DerringerSuichDesirability()[key](vs, **desirability[vst][key])
            else:
                raise RuntimeError(f"Inside the desirability dictionary you provided for the variable = vina_scores[{vst}] a non implemented key = {key}. Only are possible: 'w' (standing for weight) and any possible Derringer-Suich desirability function: {utils.DerringerSuichDesirability().keys()}.")
        base *= d**w
        exponent += w

    # Average
    #D = (w_qed*d_qed + w_sa_score*d_sa_score + sum([w_vina_score*d_vina_score for w_vina_score, d_vina_score in zip(w_vina_scores, d_vina_scores)])) / (w_qed + w_sa_score + sum(w_vina_scores))
    # Geometric mean
    # D = (d_qed**w_qed * d_sa_score**w_sa_score * np.prod([d_vina_score**w_vina_score for d_vina_score, w_vina_score in zip(d_vina_scores, w_vina_scores)]))** (1/(w_qed + w_sa_score + sum(w_vina_scores)))
    D = base**(1/exponent)
    # And because we are minimizing we have to return
    Individual.cost = 1 - D
    return Individual


if __name__ == '__main__':
    pass
    from moldrug import utils
    from rdkit import Chem
    import tempfile
    tmp_path = tempfile.TemporaryDirectory()
    I = utils.Individual(Chem.MolFromSmiles('Cn1c(=O)c2c(ncn2C)n(C)c1=O'))
    vina_score, pdbqt = vinadock(
        Individual = I,
        wd = tmp_path.name,receptor_pdbqt_path = '/home/ale/mnt/smaug/BI/challenges/v2.0.0/Cost/caffeine/3rfm_H.pdbqt',
        boxcenter = [7.76,-33.41,-32.85],
        boxsize = [23.4,23.4,23.4],
        exhaustiveness = 4,
        ncores = 4,
        constraint= True,
        constraint_type= 'score_only',
        constraint_ref = Chem.MolFromMolFile('/home/ale/mnt/smaug/BI/challenges/v2.0.0/Cost/caffeine/ligand_H.sdf'),
        constraint_receptor_pdb_path = '/home/ale/mnt/smaug/BI/challenges/v2.0.0/Cost/caffeine/3rfm.pdb',
        constraint_num_conf = 100,
        constraint_minimum_conf_rms = 0.01,       
        )
    # print(pdbqt)
    print(vina_score)
    # from meeko import PDBQTMolecule
    # pdbqtfile = os.path.join(tmp_path.name, 'pdbqt.pdbqt')

    # pdbqt_mol = PDBQTMolecule.from_file(os.path.join(tmp_path.name, '0_out.pdbqt')).export_rdkit_mol()
    
    # print(Chem.MolToMolBlock(pdbqt_mol))
    # NewI = fitness.CostMultiReceptorsOnlyVina(
    #     Individual = I,
    #     wd = tmp_path.name,
    #     receptor_pdbqt_path = [receptor_pdbqt_path, receptor_pdbqt_path],
    #     vina_score_type = ['min', 'max'],
    #     boxcenter = [box['boxcenter'], box['boxcenter']],
    #     boxsize = [box['boxsize'], box['boxsize']],
    #     exhaustiveness = 4,
    #     ncores = 4,
    #     constraint= True,
    #     constraint_type= 'local_only',
    #     constraint_ref = [Chem.MolFromMolFile('/home/ale/TEST/t/x0161_lig.sdf'), Chem.MolFromMolFile('/home/ale/TEST/t/x0161_lig.sdf')],
    #     constraint_receptor_pdb_path = ['/home/ale/TEST/t/x0161_prot.pdb', '/home/ale/TEST/t/x0161_prot.pdb'],
    #     constraint_num_conf = 100,
    #     constraint_minimum_conf_rms = 0.01,       
    #     )
    # print(NewI.cost, NewI.vina_score)
