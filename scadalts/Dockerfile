FROM eclipse-temurin:11-jdk-jammy

ENV SCADA_LTS_VERSION=2.7.8.1 \
    CATALINA_HOME=/usr/local/tomcat \
    MYSQL_ROOT_PASSWORD=root \
    MYSQL_DATABASE=scadalts \
    MYSQL_USER=root \
    MYSQL_PASSWORD=root \
    TOMCAT_USER=tcuser \
    TOMCAT_PASSWORD=tcuser

# Install dependencies
RUN apt-get update && \
    apt-get install -y wget unzip supervisor mariadb-server libjaxb-api-java libjaxb-java libactivation-java \
    gnupg curl && \
    rm -rf /var/lib/apt/lists/*

# Fake systemctl so wazuh-agent postinstall doesn't fail
# Must come AFTER mariadb-server so mariadb's postinstall can initialize the system database
RUN printf '#!/bin/bash\necho "[fake-systemctl] $@"\nexit 0\n' \
    > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl


# Install Tomcat
RUN wget https://archive.apache.org/dist/tomcat/tomcat-9/v9.0.109/bin/apache-tomcat-9.0.109.tar.gz -O /tmp/tomcat.tar.gz && \
    tar xzf /tmp/tomcat.tar.gz -C /usr/local && \
    mv /usr/local/apache-tomcat-9.0.109 $CATALINA_HOME && \
    rm /tmp/tomcat.tar.gz

# Copy JAXB + activation jars into Tomcat lib
RUN cp /usr/share/java/jaxb-*.jar /usr/local/tomcat/lib/ && \
    cp /usr/share/java/*activation*.jar /usr/local/tomcat/lib/ || true


# Download SCADA-LTS WAR and deploy as ROOT
RUN wget https://github.com/SCADA-LTS/Scada-LTS/releases/download/v${SCADA_LTS_VERSION}/Scada-LTS.war \
         -O $CATALINA_HOME/webapps/ROOT.war && \
    mkdir -p $CATALINA_HOME/webapps/ROOT && \
    cd $CATALINA_HOME/webapps/ROOT && \
    jar -xf ../ROOT.war

# Add MySQL JDBC driver
RUN wget https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-j-8.3.0.tar.gz -O /tmp/mysql-connector.tar.gz && \
    tar xzf /tmp/mysql-connector.tar.gz -C /tmp && \
    mv /tmp/mysql-connector-j-8.3.0/mysql-connector-j-8.3.0.jar $CATALINA_HOME/lib/ && \
    rm -rf /tmp/mysql-connector*

# Prepare runtime dirs and enable MariaDB error log
RUN mkdir -p /var/lib/mysql /run/mysqld /var/log/supervisor /var/log/mysql && \
    chown -R mysql:mysql /var/lib/mysql /run/mysqld /var/log/mysql && \
    printf '[mysqld]\nlog_error=/var/log/mysql/error.log\n' > /etc/mysql/conf.d/logging.cnf
VOLUME /var/lib/mysql

# Add configs
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY init.sh /init.sh
RUN chmod +x /init.sh


# Add Tomcat JNDI DataSource for SCADA-LTS
RUN sed -i '/<\/Context>/i \
  <Resource name="jdbc/scadalts" auth="Container" \
            type="javax.sql.DataSource" \
            maxTotal="100" maxIdle="30" maxWaitMillis="10000" \
            username="scada" password="scada" \
            driverClassName="com.mysql.cj.jdbc.Driver" \
            url="jdbc:mysql://localhost:3306/scadalts?serverTimezone=UTC&amp;useSSL=false&amp;allowPublicKeyRetrieval=true"/>' \
    $CATALINA_HOME/conf/context.xml




COPY 1.png /usr/local/tomcat/static/uploads/1.png
COPY seed_project_data.sql /seed_project_data.sql

# Cyber fault-injection tooling (see docs/cyber-vs-physical-fault-injection-design.md)
COPY cyber_injects /opt/cyber_injects

# Install Wazuh agent
RUN curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH \
    | gpg --no-default-keyring \
      --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import \
    && chmod 644 /usr/share/keyrings/wazuh.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] \
       https://packages.wazuh.com/4.x/apt/ stable main" \
       > /etc/apt/sources.list.d/wazuh.list \
    && apt-get update \
    && WAZUH_MANAGER=192.168.90.20 WAZUH_AGENT_NAME=scadalts apt-get install -y wazuh-agent \
    && rm -rf /var/lib/apt/lists/*

# Monitor Tomcat catalina log, access logs, and MariaDB error log
RUN sed -i 's|</ossec_config>|<localfile>\n    <log_format>syslog</log_format>\n    <location>/usr/local/tomcat/logs/catalina.out</location>\n  </localfile>\n  <localfile>\n    <log_format>syslog</log_format>\n    <location>/usr/local/tomcat/logs/localhost_access_log*.txt</location>\n  </localfile>\n  <localfile>\n    <log_format>syslog</log_format>\n    <location>/var/log/mysql/error.log</location>\n  </localfile>\n</ossec_config>|' \
    /var/ossec/etc/ossec.conf

EXPOSE 8080 3306

ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="HMI"
CMD ["/usr/bin/supervisord", "-n"]