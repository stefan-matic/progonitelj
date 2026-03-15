I wanna standardize how we approach software development, what is used, what is in our allow list, mitigate supply chain attacks, use some kind of local repo for all packages with my approved versions. The goal is to approach this in every programming language and framework, as well as docker images

Basically, if I define that docker image alpine is a certain version the user at local development and the devops pipeline can only use this version of alpine. Similar to programming languages, for example python modules, i define that numpy can be used from our repository but it cannot be lower than a certain version but it also can't be a version that has >9.0 CVE, and I need this for all major programming languages

It should span for Docker images, python packages, php, go, npm, bun etc. To have some kind of uniform DevOps way of saying "This is what is allowed and these versions we're ok with. If a user requests a newer or some package we don't have we should get a request for it to add it, via PR or something.

This tool should be 0-cost, we cannot use saas services, only something that's actually open-source.
We also wanna prevent sudden repo deletions or major changes (vendir could help here)
Container vulnerability scanning.
Managing local versions of tools like node or whatever the framework is, a set of defined allowed tooling
Also utilize justfile and pre-commit for some best practices

List of tools i know that might be a good fit to make this

https://github.com/aquasecurity/trivy
https://github.com/dependabot
https://github.com/renovatebot/renovate
https://asdf-vm.com/
https://mise.jdx.dev/getting-started.html
https://github.com/carvel-dev/vendir

Komodo + Forgejo + Renovate for handling image updates
https://www.reddit.com/r/selfhosted/s/9uuQMi2s0N
~`
