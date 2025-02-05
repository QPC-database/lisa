# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2018, Arm Limited and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys

from lisa.target import Target
from lisa.utils import ArtifactPath
from lisa.tests.base import TestMetric, ResultBundle, TestBundle
from lisa.wlgen.sysbench import Sysbench


class CapacitySanity(TestBundle):
    """
    A class for making sure capacity values make sense on a given target

    :param capacity_work: A description of the amount of work done on the
      target, per capacity value ({capacity : work})
    :type capacity_work: dict
    """

    def __init__(self, res_dir, plat_info, capacity_work):
        super().__init__(res_dir, plat_info)

        self.capacity_work = capacity_work

    @classmethod
    def _from_target(cls, target: Target, *, res_dir: ArtifactPath = None, collector=None) -> 'CapacitySanity':
        """
        :meta public:

        Factory method to create a bundle using a live target
        """
        with target.cpufreq.use_governor("performance"):
            sysbench = Sysbench(target, res_dir=res_dir)

            cpu_capacities = target.sched.get_capacities()
            capa_work = {capa: sys.maxsize for capa in list(cpu_capacities.values())}
            for cpu in list(cpu_capacities.keys()):
                with collector:
                    output = sysbench(cpus=[cpu], max_duration_s=1).run()
                # We could save the work done on each CPU, but we can make
                # things simpler and just store the smallest amount of work done
                # per capacity value.
                capa = cpu_capacities[cpu]
                capa_work[capa] = min(capa_work[capa], output.nr_events)

        return cls(res_dir, target.plat_info, capa_work)

    def test_capacity_sanity(self) -> ResultBundle:
        """
        Assert that higher CPU capacity means more work done
        """
        sorted_capacities = sorted(self.capacity_work.keys())
        work = [self.capacity_work[cap] for cap in sorted_capacities]

        # Check the list of work units is monotonically increasing
        work_increasing = (work == sorted(work))
        res = ResultBundle.from_bool(work_increasing)

        capa_score = {}
        for capacity, work in self.capacity_work.items():
            capa_score[capacity] = TestMetric(work)

        res.add_metric("Capacity to performance", capa_score)

        return res

# vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab
