<ruby>

require 'json'
require 'net/http'
require 'securerandom'
require 'uri'

def get_exploit_info(exploit_name)
    exploit = self.framework.modules.create(exploit_name)
    description = get_exploit_description(exploit)
    privileged = exploit.privileged ? "Elevated" : ""
    platforms = exploit.target_platform.platforms.map {|plat| plat.realname }

    params = []
    for name, option in exploit.options
        if option.required && option.default.nil?
            params.push(name)
        end
    end

    data = {
        "name" => exploit.name,
        "description" => description,
        "platform" => platforms,
        "privilege" => exploit.privileged ? "Elevated" : "",
        "module" => exploit.realname,
        "params" => params
    }
end

def get_exploit_description(exploit)
    description = Rex::Text.compress(exploit.description)
    description << "\n\n"

    if (exploit.options.has_options?)
      description << "Basic options:\n\n"
      description << ::Msf::Serializer::ReadableText.dump_options(exploit, "  ")
    end

    adv_opts = ::Msf::Serializer::ReadableText.dump_advanced_options(exploit, "   ")
    description << "\nAdvanced options:\n\n"
    description << "#{adv_opts}\n" if (adv_opts and adv_opts.length > 0)

    description << ::Msf::Serializer::ReadableText.dump_references(exploit, "  ")

    return description
end

def convert_to_ability(exploit)
    command = 'msfconsole -x "use ' + exploit['module'] + '; '
    for param in exploit['params']
        command += 'set ' + param + ' ' + '#{msf.' + param + '}; '
    end
    command += 'run"'

    os = get_os
    executor = (os == "windows" ? "cmd" : "sh")

    ability = {
        "ability_id" => SecureRandom.uuid,
        "tactic" => "metasploit",
        "technique_name" => "metasploit",
        "technique_id" => "T1349",
        "name" => exploit['name'],
        "description" => exploit['description'],
        "privilege" => exploit['privilege'],
        "executors" => [{
            "command" => command,
            "timeout" => 60,
            "platform" => os
        }]
    }
    return ability
end

def get_os
    if (/cygwin|mswin|mingw|bccwin|wince|emx/ =~ RUBY_PLATFORM) != nil
        return "windows"
    elsif (/darwin/ =~ RUBY_PLATFORM) != nil
        return "darwin"
    else
        return "linux"
    end
end

def save_ability(ability, c2_uri, c2_key)
    uri = URI.parse(c2_uri + '/api/v2/abilities')
    header = {
        'Content-Type' => 'text/json',
        'KEY' => c2_key
    }
    http = Net::HTTP.new(uri.host, uri.port)
    request = Net::HTTP::Post.new(uri, header)
    request.body = ability.to_json
    response = http.request(request)
end

c2_uri = ARGV.shift || 'http://0.0.0.0:8888'
c2_key = ARGV.shift || 'ADMIN123'

for exploit_name in self.framework.exploits.keys
    exploit = get_exploit_info(exploit_name)
    ability = convert_to_ability(exploit)
    response = save_ability(ability, c2_uri, c2_key)
end

exit(true)

</ruby>

quit
