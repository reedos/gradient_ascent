export default function ExampleOverview({overview, task, outcome}: {overview:string;task:string;outcome:string}) {
  return <section className="walk-overview" aria-label="About this guided example">
    <h3>What you’ll walk through</h3><p>{overview}</p>
    <div className="walk-overview-grid"><div><h4>The task in this version</h4><p>{task}</p></div><div><h4>What to look for</h4><p>{outcome}</p></div></div>
    <p className="walk-overview-note">The setting makes the example concrete. Carry the underlying pattern into your own work; adapt the sources, tools, and level of oversight to your task.</p>
  </section>;
}
