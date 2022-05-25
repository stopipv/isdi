#  ISDi Contribution Guidelines

We welcome contributions to ISDi in all forms, including contributing coding, opening issues, writing documentation, or otherwise providing feedback. This page is intended to provide recommendations and guidelines for those looking to get involved.

## Slack Channel and Meetings

In addition to participating in discussions through issue threads, you can also join the #isdiv2 channel on the [Mobile Spyware Slack channel](mobilespywareproject.slack.com). The Slack channel includes a calendar invitation to our bi-weekly meeting to discuss the direction of this project. You may also view the minutes from these meetings here. Before joining the Slack channel or the bi-weekly meetings, please review our code of conduct.

## Code of Conduct

1) Be respectful in all areas of discussion, including but not limited to issue threads, Slack discussion, and in-person meetings. This means being considerate (not dismissive) of suggestions or opinions, adopting a collaborative rather than hostile tone, and not making assumptions about fellow contributors knowledge. If you're not sure what someone meant, ask--politely.

  
2) Harassment, threats, violence and any other forms of abuse will be given a zero-tolerance policy. Violators of this rule will be immediately banned from all contribution avenues with further action taken as necessary. This project is intended to help survivors and victims of tech abuse, and we will obviously take all steps possible to prevent and remove such behavior in this community.  
  
3) Relatedly, if you witness or experience behavior that violates points 1 or 2, we encourage you to raise it either publicly in the Slack channel or meetings or privately with one of the maintainers.  
  
4) We endorse quality and maintainable code. This includes combining commits that address a single issue into one dedicate commit, continuous testing between pull requests, and well-documented, readable code. Pull requests that violate this will be offered a (gentle! see rule #1) corrective. However, we understand that everyone has different levels of comfort with contributing to open source code, and some practices may be new or intimidating. If you're unsure, feel free to ask!  
  

## Creating an Issue

First, check to see if an issue has already been created for this problem by searching the Issues tab. If one already exists, feel free to join the discussion in the existing issue, but avoid duplicating issues.  
  
If an issue has not already been created, you may open a new issue. Please choose a title that is succinct but clear. If the issue is describing an error, please document as much information as possible as to the circumstances under which the issue appeared (e.g. What operating system are you running? What is the model of the device checked? What is the full history of commands you ran?) as well as a screenshot of the error message.  
  
Please use the appropriate labels to tag the issue, namely bug, enhancement, question, documentation, and good first issue. This not only helps us prioritize issues, but helps contributors with a specific interest find relevant issues. A good first issue label should be given to issues with minor fixes (e.g. syntax errors) or that are contains to one to two files. If you're not sure if an issue is appropriate for a good first issue, mention it in the issue description.

  

## Submitting a Pull Request

To contribute code or documentation, please use the fork-branch-pull request workflow, outline below:  
  
1) Fork this repository ([Github guide](https://docs.github.com/en/get-started/quickstart/contributing-to-projects)) and create a local clone.

2) Create a branch ([Github guide](https://guides.github.com/introduction/flow/)).

3) Push the edits you wish to make to the forked branch you created.

4) Open a pull request to the stopiv/isdi repo and provide a brief description of your changes. If your pull request addresses a specific issue(s), please tag them in your pull request. If no issue exists, open an issue and tag it in your pull request.

5) Ensure your pull request passes any existing workflow checks.  
6) You're done! A maintainer will run and test your code and merge it into the main codebase if it is accepted. Keep an eye out for any comments from maintainers asking you to address suggested changes.

  

## Reviewing and Merging a Pull Request
Currently, only maintainers are allowed to review and merge pull requests. In the future, we plan to use continuous integration workflows to automatically test PRs and ensure compatibility among as many devices as possible. 

However, for now, it is acceptable to check the PR against your own device and merge it if it passes. If the PR is for a platform for which you lack a testable device, please refrain from merging the PR until an appropriate device can test it. Maintainer contact information and device testing capability is updated in the [ISDi Maintainers + Devices](https://docs.google.com/spreadsheets/d/1DpYI9LL-CnPXdjzxUh1r5XYO4f0dVX8XpA5WxziVlUA/edit?usp=sharing) and reproduced below.

### Maintainers:  
The following individuals <@github> are maintainers of the code base and have permission to merge pull requests: 
* Rahul Chatterjee <`@rchatterjee`>, Pixel 4  
* Tom Ristenpart  <`@tomrist`>
* Nolan Earl  <@shffrror>
* Martijn Grooten<@>  
* Stef Hart
* Grant V <`@grantv9`>, iPhone 8
* Lana R <`@lanamorgan`>, iPhone 8
	
