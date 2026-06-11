# PRD: Data Warehouse for Education
An open source, modern data stack for school networks (in particular Multi Academy Trusts)

- **Status:** Proposal
- **Date:** May 26, 2026

## Problem alignment

Multi Academy Trusts (MATs) have shown interest in following Uncommon Schools’ data intensive best practices, but find this difficult to do effectively with data tied up in a variety of different SaaS tools. Many school systems at the beginning of their data journey struggle with relatively simple tasks that aren’t already directly handled by their MIS/SIS tools: e.g. calculating turnover stats. Getting to a more advanced stage where school networks can regularly look at assessment data to identify gaps in learning requires being able to pull data from multiple systems, clean and transform that data into marts, and create visualizations that are accessible to teachers and school leaders. Luckily many modern businesses and organizations are using data to run their organizations effectively; schools can leverage open, standard data tools for this purpose. Several MAT leaders have expressed interest in piloting a project. 

### High level approach

Create a modern data stack for schools, using industry standard, largely open source components. Make the deployment code and other glue code for hosting and running this stack open source, so that school networks can collaborate on the implementation of the system and have control of their own data outside of SaaS silos. School networks can self-host the open source project; alternatively Ponder will offer a hosted version of DWE. 

We will refer to the open source project as DWE-core; hosted DWE will make use of this code as well as any additional code needed to manage multiple installations. The user experience for teachers, school leaders, and analysts should remain largely the same.

In addition to licensing DWE-core and other projects as open source, Ponder sees an advantage in creating a collaborative community of people providing technical support for schools; sharing experiences, code and expertise. Ponder believes there might be value in sharing our technical work, even if the code libraries are not used directly.

We recognize that there is a cost/convenience tradeoff between using open source components and using cloud based managed services. Our initial plan is to lean into open source components to give schools more flexibility and control and to manage costs. This decision could be revisited if it turns out that total cost of ownership would be optimal using more managed services, on a component by component basis. The larger goal is sharing our technical knowledge with other school systems to achieve better outcomes with reduced costs. 

### Goals and Success

Initial goals are demonstration of practical value via use of DWE:
- One or more school networks is using Ponder’s hosted version of DWE
- One or more school networks is using DWE-core via self-hosting (either by internal IT teams or via a contractor)

Additional goals indicating the value of structuring DWE as an open source project:
- One or more school networks (or someone working on their behalf) downloads DWE and kicks the tires
- DWE receives contributions from outside Ponder, ideally from a school network (or someone working on their behalf)
- School networks share or contribute DWE related resources (connectors, dashboards, etc.)

For the initial phases, the goal is providing value to a few school networks. If we achieve this success, we will revisit to consider scaling the project.

## Solution alignment

### Key Features

A school network data platform needs these features:
- Connectors to load data from source systems into a data lakehouse for further processing. A school network should be able to use existing standard connectors or create their own connectors for newly added data sources.
- Mechanism for schools to create business logic that transforms data from source tables into data marts or models, with modular, code based, version controlled transformations
- Centralized semantic layer and metrics store, providing consistent business definitions 
- Visualization tools to enable school leaders, analysts and teachers to explore and visualize data, as well as create regular reports
- SQL tools (and possibly AI chat interfaces) to query data marts / models to ask questions of the data
- Orchestration tools to schedule, manage and monitor data pipeline operations 
- Data governance features to provide access controlled, versioned data with audit trails
- Infrastructure as code to deploy and manage the platform
- GDPR Readiness, including support for data subject rights, as well as meeting security, audit and accountability requirements

### Key Decisions

| Issue | Decision | Tool |
| --- | --- | --- |
| Tech stack | Use stack similar to stack Uncommon Schools is using, replacing some pieces with open source components. | Proposed |
| Open Source License for data infrastructure code written by Ponder | Apache 2.0 – same license as most of the components | Proposed |
| Copyright/ownership of code | Ponder. Includes code written by ponder and any PRs submitted by the community. | Proposed |
| Governance model | Ponder manages project governance internally, making decisions visible through ADRs. Ponder will accept PRs and track bugs/requests in github. Ponder will revisit if external collaborators are contributing to the project. | Proposed |
| Mission statement/northstar | Mission statement should build on values/ethos work we’ve done for website and presentations. Values: (1) Affordability (2) Vendors are co-pilots (equal footing between schools and vendors, schools maintain control and independence) (3) Transparent architecture (share components and best practices) | draft needed |
| Transparent project management, including: Downloadable code, Version control, Issue tracker, Code submissions, and Project tracking | Github | Accepted |
| Documentation | Lives in Github / Github Pages. Recommended that we start here for soft launch, may use something else for user facing documentation eventually | Proposed |
| Communication Channels | Stick to existing communication channels (substack, github, email) Philosophy: keep it minimal before we have a deployment / are ready to scale | Proposed | 
| Code of Conduct | Use [Contributor Covenant](https://www.contributor-covenant.org/) | draft needed |



