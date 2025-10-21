export {
    getAbilityFacts,
    getAbilityPlatforms,
};

function getAbilityFacts(ability) {
    let factTraits = [];
    if (ability.executors) {
        ability.executors.forEach((exec) => {
            if (exec.command) {
                // Find all abilities where an executor has a command with a #{} fact variable
                const match = [ ...exec.command.matchAll(/#{(.*?)}/gm) ];
                if (match && match.length > 0) {
                    factTraits = factTraits.concat(match.map((variable) => variable[1])); 
                }
            }
        });
    }
    return [ ...new Set(factTraits) ];
}
function getAbilityPlatforms(ability, withName = false) {
    return [...new Set(ability.executors.map((exec) => withName ? `${exec.platform} (${exec.name})` : exec.platform))];
}
