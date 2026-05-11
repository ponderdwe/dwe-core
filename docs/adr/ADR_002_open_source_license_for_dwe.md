# ADR-002: Open Source License for DWE (Data & Web Environment)

- **Date:** 2026-02-27
- **Status:** Proposed

## Context

Ponder is going to open source the core code used for its Data Warehouse for Education, which we’re calling DWE-Core. Ponder is creating this open source project to facilitate collaboration with school networks and ed-tech partners on data infrastructure in schools. Many of DWE-Core’s components are open source – below is a table listing components considered in our initial PRD: 

| Open Source Component | License |
| --- | --- |
| Iceberg | Apache 2.0 |
| Trino | Apache 2.0 |
| Nessie | Apache 2.0 |
| Airflow | Apache 2.0 |
| DBT-Core | Apache 2.0 |
| Superset | Apache 2.0 |
| Docker-engine | Apache 2.0 |
| Open-tofu (fork of Terraform) | Mozilla Public License 2.0 |
| Coder-community | GNU Affero General Public License - GNU Project - Free Software Foundation |
| Cube Core | Client - MIT Backend - Apache 2.0 |

Like many of these products, Ponder will also offer a paid, hosted version of DWE that makes use of DWE-Core. Ponder would like to have a generally permissive license for DWE-Core with minor protections to not impede providing this service to schools.

## Decision

The project will use the Apache 2.0 License.  

Permissions:

- Commercial use: licensed material and derivatives may be used for commercial purposes.
- Distribution: licensed material may be distributed
- Modifications: licensed material may be modified
- Patent use: license provides an express grant of patent rights from contributors
- Private use: licensed material may be used and modified in private

Conditions:

- License and copyright notice: a copy of the license and and copyright notice must be included with the licensed material.
- Change notice: changes made to the licensed material must be documented

Limitations:

- Liability limitation: license includes a limitation of liability
- Trademark use limitation: license explicitly states that it does not grant trademark rights
- Warranty limitation: license explicitly states it does not provide any warranty

The Apache 2.0 license is very similar to the MIT license, with more explicit language around patents and trademarks.
