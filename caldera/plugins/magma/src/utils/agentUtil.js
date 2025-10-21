export {
    getAgentStatus
};

function getAgentStatus(agent) {
    if (!agent.last_seen) return '';
    let lastSeen = new Date(agent.last_seen).getTime();
    let msSinceSeen = Date.now() - lastSeen;
    // Give a buffer of 1 minute to mark an agent dead
    let isAlive = (msSinceSeen < (agent.sleep_max * 1000));

    if (msSinceSeen <= 60000 && agent.sleep_min === 3 && agent.sleep_max === 3 && agent.watchdog === 1) {
        return 'pending kill'
    } else {
        return msSinceSeen <= 60000 || isAlive ? 'alive' : 'dead';
    }
}
