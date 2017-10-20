#!/usr/bin/python3
# Copyright 2013, 2014, 2017 Conix Cybersécurité
# Copyright 2013 Adrien Chevalier (bl2ru)
# Copyright 2013, 2014 Alexandre Deloup (bl2ru)
# Copyright 2017 Robin Marsollier
# Copyright 2017 Michael Muenz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import argparse
import os
import re

#####
# To add a rule class while keeping the code clean:
# 1. add the base rule thereafter
# 2. create the gen_SMTHG_rule() function that is going to generate the rules
#        using the baserule defined before
# 3. modify the generate_rules() function to call your new generator
#####
IP_UDP_BASERULE = 'alert udp $HOME_NET any -> {} any (msg:"{} - {} - UDP traffic to {}"; classtype:trojan-activity; reference:url,{}; sid:{}; rev:1;)'
IP_TCP_BASERULE = 'alert tcp $HOME_NET any -> {} any (msg:"{} - {} - TCP traffic to {}"; flow:to_server,established; classtype:trojan-activity; reference:url,{}; sid:{}; rev:1;)'
IP_BASERULE = 'alert ip $HOME_NET any -> {} any (msg:"{} - {} - IP traffic to {}"; classtype:trojan-activity; reference:url,{}; sid:{}; rev:1;)'
#DNS_BASERULE = 'alert udp $HOME_NET any -> any 53 (msg:"{} - {} - DNS request for {}"; content:"|01 00 00 01 00 00 00 00 00 00|"; depth:20; offset: 2; content:"{}"; flow:to_server; fast_pattern:only; nocase; classtype:trojan-activity; reference:url,{}; sid:{}; rev:1;)'
DNS_BASERULE = 'alert dns $HOME_NET any -> any 53 (msg:"{} - {} - DNS request for {}"; dns_query; content:"{}"; nocase; reference:url,{}; sid:{};)'
URL_BASERULE = 'alert http $HOME_NET any -> $EXTERNAL_NET $HTTP_PORTS (msg:"{} - {} - Related URL ({})"; content:"{}"; http_uri;{} flow:to_server,established; classtype:trojan-activity; reference:url,{}; sid:{}; rev:1;)'
TLS_BASERULE = 'alert tls $HOME_NET any -> $EXTERNAL_NET any (msg:"{} - {} - Related TLS SNI ({})"; tls_sni; content:"{}";flow:to_server,established; classtype:trojan-activity; reference:url,{}; sid:{}; rev:1;)'
MD5_BASERULE = 'alert tcp any [$HTTP_PORTS, 25] -> $HOME_NET any (msg:"{} - {} - MD5 hash found in blacklist {}"; classtype:trojan-activity; filestore; filemd5:{}; reference:url,{}; sid:{}; rev:1;)'


class Surigen:
    _sid_ = 0
    _org_ = ""

    def __init__(self, org, sid):
        '''
        get sid to use for this run
        '''
        if not sid or sid == "log":
            try:
                with open(".sid_log_file", "r", encoding="utf-8") as f_sid_log_file:
                    line = f_sid_log_file.readline()
                    self._sid_ = int(line)
            except FileNotFoundError:
                print("[-] .sid_log_file not found, starting SID from 5100000")
                return
            except PermissionError as err:
                print(err)
                print("[+] Aborting!")
                quit(0)
        else:
            self._sid_ = sid
        Surigen._org_ = org

    def __del__(self):
        '''
        save sid to use for next run
        '''
        try:
            with open(".sid_log_file", "w", encoding="utf-8") as f_sid:
                f_sid.write("{}".format(self._sid_))
        except PermissionError as err:
            print(err)
            print("[-] sid not saved, be carefull")
            return False
        return True

    def gen_dns_rule(self, name, domain, ref):
        '''
        Generate suricata rule for a domain
        '''
        dns_request = domain
        rule = (DNS_BASERULE.format(self._org_, name, domain, dns_request, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_-1

    def gen_uri_rule(self, name, url, ref):
        '''
        Generate suricata rule for an url
        '''
        uri = url.split("?")[0]
        # If there are many "?" in the complete url, colapse them
        uri_params = "?".join(url.split("?")[1:])
        rule_content = ""
        if uri_params:
            params = uri_params.split("&")
            rule_content = ' content:"?{}=";'.format(params[0].split("=")[0])
            for param in params[1:]:
                # escaping ';'
                param = param.replace(';', r'|3b|')
                rule_content += ' content:"&{}=";'.format(param.split("=")[0])
        rule = (URL_BASERULE.format(self._org_, name, uri, uri, rule_content, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_ - 1

    def gen_ip_rule_udp(self, name, ip_addr, ref):
        '''
        Generate suricata rule for an IP, traffic over udp
        '''
        rule = (IP_UDP_BASERULE.format(ip_addr, self._org_, name, ip_addr, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_-1

    def gen_ip_rule_tcp(self, name, ip_addr, ref):
        '''
        Generate suricata rule for an IP, traffic over tcp
        '''
        rule = (IP_TCP_BASERULE.format(ip_addr, self._org_, name, ip_addr, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_-1

    def gen_ip_rule(self, name, ip_addr, ref):
        '''
        Generate suricata rule for an IP
        '''
        rule = (IP_BASERULE.format(ip_addr, self._org_, name, ip_addr, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_-1

    def gen_tls_rule(self, name, domain, ref):
        '''
        Generate suricata TLS SNI rule for a domain
        '''
        rule = (TLS_BASERULE.format(self._org_, name, domain, domain, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_-1

    def gen_md5_rule(self, name, filepath, ref):
        '''
        Check if filename is a path or a filename
        :param name: Threat name
        :param filepath: Can be a path or a filename. If your md5 file is in /etc/suricata/rules you can just pass a filename.
                         Else, you need a full path.
        :param ref: reference_url
        :return: The generated rule and the new sid
        '''
        rule = (MD5_BASERULE.format(self._org_, name, os.path.basename(filepath), filepath, ref, self._sid_))
        self._sid_ += 1
        return rule, self._sid_-1


def __split_line__(line):
    '''
    Cut the line to extract the different fields
    '''
    (name, ref_url, ioc) = line.split(' ')
    name = name.strip()
    ref_url = ref_url.strip()
    ioc = ioc.strip()
    return name, ioc, ref_url


def __generate_rules__(gen, csv_file):
    '''
    Determine ioc type and call the differents generators
    '''
    try:
        with open(csv_file, "r") as f_input:
            rules = []
            for line in f_input:
                line = line.strip()
                (name, ioc, ref_url) = __split_line__(line)
                if (ioc.startswith("/") or ioc.startswith("http")) and not os.path.isfile(ioc):
                    print("a")
                    # URI it is
                    (rule, sid) = gen.gen_uri_rule(name, ioc, ref_url)
                    rules.append(rule)
                elif re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ioc):
                    # IP it is
                    # (rule, sid) = gen.gen_ip_rule_udp(name, ioc, ref_url)
                    # rules.append(rule)
                    # (rule, sid) = gen.gen_ip_rule_tcp(name, ioc, ref_url)
                    # rules.append(rule)
                    (rule, sid) = gen.gen_ip_rule(name, ioc, ref_url)
                    rules.append(rule)
                elif os.path.isfile(ioc):
                    (rule, sid) = gen.gen_md5_rule(name, ioc, ref_url)
                    rules.append(rule)
                else:
                    # Well, by lack of other option, let's say it is a FQDN
                    (rule, sid) = gen.gen_dns_rule(name, ioc, ref_url)
                    rules.append(rule)
                    (rule, sid) = gen.gen_uri_rule(name, ioc, ref_url)
                    rules.append(rule)
                    (rule, sid) = gen.gen_tls_rule(name, ioc, ref_url)
                    rules.append(rule)
    except PermissionError as err:
        print(err)
        print("[+] Aborting!")
        quit(0)
    return rules


def main(args):
    '''
    main
    '''
    gen = Surigen(args.emitter, args.ssid)

    #############################
    #       Generating rules
    if args.output:
        print("[+] Generating rules")
    rules = __generate_rules__(gen, args.file)

    #############################
    #       Writing rules to file or stdout
    if args.output:
        print("[+] Writing Rule file")
        try:
            with open(args.output, "a") as f_out:
                for rule in rules:
                    f_out.write("{} \n".format(rule))
        except PermissionError:
            print("[+] Can't write rule file, permission denied")
            print("[+] Rules not saved, be carefull")
    else:
        for rule in rules:
            print("{}".format(rule))


if __name__ == '__main__':
    __parser__ = argparse.ArgumentParser()
    __parser__.add_argument("file", help="Input file")
    __parser__.add_argument("--output", "-o",
                            help="Output file (default is stdout)")
    __parser__.add_argument("--ssid", "-s",
                            help="Starting sid of the generated rules", type=int)
    __parser__.add_argument("--emitter", "-e",
                            help="Emitter of the rules, default: surigen", default="surigen")
    __args__ = __parser__.parse_args()
    main(__args__)
