"""cli commands related to software management"""

from pathlib import Path
from typing_extensions import Annotated

from omni.software import easybuild_backend as eb
from omni.software import conda_backend
from omni.software import common

import typer

import os, sys

# import logging

cli = typer.Typer(add_completion = True,  no_args_is_help = True, pretty_exceptions_short = True)

sing_cli = typer.Typer(add_completion = True,  no_args_is_help = True, pretty_exceptions_short = True)
cli.add_typer(sing_cli, name = 'singularity',
              help = 'Manage singularity- (apptainer-) based software installations. Uses easybuild.')

conda_cli = typer.Typer(add_completion = True,  no_args_is_help = True, pretty_exceptions_short = True)
cli.add_typer(conda_cli, name = 'conda',
              help = 'Manage conda-based software installations. Does not use easybuild.')

module_cli = typer.Typer(add_completion = True,  no_args_is_help = True, pretty_exceptions_short = True)
cli.add_typer(module_cli, name = 'module',
              help = 'Manage module- based software installations. Uses easybuild.')


## singularity #####################################################################################

@sing_cli.command("build")
def singularity_build(
    easyconfig: Annotated[
        str,
        typer.Option(
            "--easyconfig",
            "-e",
            help="Easyconfig",
        ),
    ],
):
    """Build a singularity (fakeroot) image for a given easyconfig."""
    typer.echo(f"Installing software for {easyconfig} within a Singularity container. It will take some time.")
    
    if eb.check_easybuild_status().returncode != 0:
        raise('ERROR: Easybuild not installed')
    if eb.check_singularity_status().returncode != 0:
        raise('ERROR: Singularity not installed')

    ## check the easyconfig exists
    try:
        fp = eb.get_easyconfig_full_path(easyconfig = easyconfig, workdir = os.getcwd())
    except:
        print('ERROR: easyconfig not found.\n')
        sys.exit()
        
    ## do
    singularity_recipe = 'Singularity_' + easyconfig + '.txt'
    envmodule_name = eb.get_envmodule_name_from_easyconfig(easyconfig, workdir = os.getcwd())    
    eb.create_definition_file(
        easyconfig = easyconfig,
        singularity_recipe = singularity_recipe,
        envmodule = envmodule_name, nthreads = str(len(os.sched_getaffinity(0))))

    eb.singularity_build(easyconfig = easyconfig, singularity_recipe = singularity_recipe)
    print('DONE: recipe and image built for ' + singularity_recipe)

@sing_cli.command("push")
def singularity_push(
    docker_username: Annotated[
        str,
        typer.Option(
            "--docker_username",
            "-u",
            help="Docker username",
        ),
    ],
    docker_password: Annotated[
        str,
        typer.Option(
            "--docker_password",
            "-p",
            help="Docker password (token)",
        ),
    ],
    sif : Annotated[
        Path,
        typer.Option(
            "--sif",
            "-s",
            help="Path to the Singularity SIF file",
        ),
    ],
    oras : Annotated[
        str,
        typer.Option(
            "--oras",
            "-o",
            help="Registry's ORAS static URL, for instance oras://registry.mygitlab.ch/myuser/myproject:mytag"
        ),
    ],
):
    """Pushes a singularity SIF file to an ORAS-compatible registry"""
    typer.echo(f"Pushing {sif} to the registry {oras}.")

    eb.push_to_registry(sif = sif,
                        docker_username = docker_username,
                        docker_password = docker_password,
                        oras = oras)
    print('DONE\n.')


## conda #############################################################################################

@conda_cli.command("pin")
def pin_conda_env(
    conda_env: Annotated[
        str,
        typer.Option(
            "--env",
            "-e",
            help="Path to the conda env file.",
        ),
    ],
):
    """Pin all conda env-related dependencies versions using snakedeploy."""
    typer.echo(f"Pinning {conda_env} via snakedeploy. It will take some time.")
    conda_backend.pin_conda_envs(conda_env)
    typer.echo(f'DONE: Pinned {conda_env}\n')


# def push_singularity(
# )
## these belong to the validator, not here

@cli.command("check")
def check(
    what: Annotated[
        str,
        typer.Option(
            "--what",
            "-w",
            help="""Binary/functionality to check: \n
               --what singularity : singularity \n
               --what module      : module tool, typically lmod \n 
               --what easybuild   : easybuild \n
               --what conda       : conda \n""",
        ),
    ],        
):
    """Check whether the component {what} is available."""
    typer.echo(f"Checking whether the component {what} is available.")

    if what == 'easybuild':
        ret = eb.check_easybuild_status()
    elif what == 'module':
        # eb.export_lmod_env_vars()
        ret = eb.check_lmod_status() 
    elif what == 'singularity':
        ret =eb.check_singularity_status()
    elif what == 'conda':
        ret = eb.check_conda_status()
    else:
        raise typer.BadParameter("Bad `--what` value. Please check help (`ob software check --help`).")
    if ret.returncode == 0:
        print('OK:', ret)
    else:
        print('Failed:', ret)
