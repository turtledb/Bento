import sys
import os
import copy
import distutils.sysconfig

from cPickle \
    import \
        load, dump, dumps

from utils \
    import \
        ensure_dir
from ctasks \
    import \
        link_task
from task \
    import \
        Task
from task_manager \
    import \
        get_bld, create_tasks, topo_sort, build_dag, run_tasks, CACHE_FILE, TaskGen, CompiledTaskGen
from compiled_fun \
    import \
        compile_fun

# import necessary to register corresponding hooks
import tpl_tasks
import cython
import fortran

def apply_cpppath(task_gen):
    cpppaths = task_gen.env["CPPPATH"]
    cpppaths.extend(task_gen.env["PYEXT_CPPPATH"])
    implicit_paths = set([
        os.path.join(task_gen.env["BLDDIR"], os.path.dirname(s))
        for s in task_gen.sources])
    cpppaths = list(implicit_paths) + cpppaths
    task_gen.env["INCPATH"] = ["-I%s" % p
                                   for p in cpppaths]

def order_tasks(tasks):
    tuid_to_task = dict([(t.get_uid(), t) for t in tasks])

    task_deps, output_to_tuid = build_dag(tasks)

    yo = topo_sort(task_deps)
    ordered_tasks = []
    for output in yo:
        if output in output_to_tuid:
            ordered_tasks.append(tuid_to_task[output_to_tuid[output]])

    return ordered_tasks

pylink, pylink_vars = compile_fun("pylink", "${PYEXT_SHLINK} -o ${TGT[0]} ${SRC}", False)

pycc, pycc_vars = compile_fun("pycc", "${PYEXT_SHCC} ${PYEXT_CCSHARED} ${PYEXT_CFLAGS} ${PYEXT_INCPATH} -o ${TGT[0]} -c ${SRC}", False)

def pycc_hook(self, node):
    tasks = pycc_task(self, node)
    self.object_tasks.extend(tasks)
    return tasks

def pycc_task(self, node):
    base = os.path.splitext(node)[0]
    # XXX: hack to avoid creating build/build/... when source is
    # generated. Dealing with this most likely requires a node concept
    if not os.path.commonprefix([self.env["BLDDIR"], base]):
        target = os.path.join(self.env["BLDDIR"], base + ".o")
    else:
        target = base + ".o"
    ensure_dir(target)
    task = Task("pycc", inputs=node, outputs=target)
    task.env_vars = pycc_vars
    task.env = self.env
    task.func = pycc
    return [task]

def create_pyext(bld, name, sources):
    base = name.split(".")[-1]

    tasks = []

    task_gen = CompiledTaskGen("pyext", sources, name)
    task_gen.env.update(copy.deepcopy(bld.env))
    for v in ["CC", "CFLAGS", "LDSHARED"]:
        # braindead sysconfig returns string instead of list - we
        # should take quoting into account to do this correctly...
        task_gen.env[v] = distutils.sysconfig.get_config_var(v).split()

    apply_cpppath(task_gen)

    tasks = create_tasks(task_gen, sources)
    # XXX: hack, create a pylink task gen
    ltask = link_task(task_gen, name.split(".")[-1])
    ltask[0].func = pylink
    tasks.extend(ltask)
    for t in tasks:
        t.env = task_gen.env

    ordered_tasks = order_tasks(tasks)
    run_tasks(bld, ordered_tasks)

def create_sources(bld, name, sources):
    tasks = create_tasks(bld, sources)
    run_tasks(bld, tasks)

if __name__ == "__main__":
    bld = get_bld()
    bld.env = {"CC": ["gcc"],
            "CFLAGS": ["-W"],
            "CPPPATH": [],
            "PYEXT_CPPPATH": [distutils.sysconfig.get_python_inc()],
            "SHLINK": ["gcc", "-O1"],
            "SHLINKFLAGS": ["-shared", "-g", "-O1"],
            "F77": ["gfortran"],
            "F77FLAGS": ["-W", "-g"],
            "SUBST_DICT": {"VERSION": "0.0.2"},
            "VERBOSE": False,
            "BLDDIR": "build",
    }

    create_sources(bld, "template", sources=["src/foo.h.in"])
    create_pyext(bld, "_bar", ["src/hellomodule.c", "src/foo.c"])
    create_pyext(bld, "_von", ["src/vonmises_cython.pyx"])
    create_pyext(bld, "_yo", ["src/bar.f"])

    with open(CACHE_FILE, "w") as fid:
        dump(bld.cache, fid)
