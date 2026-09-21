import cases from '../../../examples/practical_labs/cases.json';
export const practicalLabs = cases;
export const labsFor = (slug:string) => practicalLabs.filter(lab=>lab.techniques.includes(slug));
export function labMarkdown(id:string){
 const lab=practicalLabs.find(l=>l.id===id);
 if(!lab)return '';
 return [`# ${lab.title}`,lab.level,lab.summary,'Synthetic inputs. Authored reference output. See prototype review for local-model smoke-test scope.',`## Task\n${lab.task}`,`## Sources\n${lab.data.map(d=>`### ${d.id}\n${d.text}`).join('\n\n')}`,`## Design\n${lab.steps.map(([title,body])=>`### ${title}\n${body}`).join('\n\n')}`,`## Important distinction\n${lab.nuance}`,`## Acceptance criteria\n${lab.rubric.map(r=>'- '+r).join('\n')}`,`## Failure case\n${lab.failure}`,`## Task brief\n${lab.prompt}`,`## Authored reference\n\`\`\`json\n${JSON.stringify(lab.expected,null,2)}\n\`\`\``,`## Adaptation\n${lab.adapt}`,`## Limits\n${lab.limits}`].join('\n\n')+'\n';
}
